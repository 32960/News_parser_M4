from uuid import UUID

from fastapi import HTTPException
from sqlmodel import Session, select

from app.api.schemas import SourceUpdate, SourceWrite
from app.models import NewsItem, Source, SourceType
from app.parsers import get_parser
from app.parsers.telegram_parser import TelegramParser


class SourceService:
    @staticmethod
    def validate_and_normalize_url(
        source_type: SourceType, url: str
    ) -> str:
        """
        Check that we have a parser for this address.
        For Telegram also normalize to https://t.me/<username>.
        """
        parser = get_parser(source_type, url)
        if parser is None:
            if source_type == SourceType.SITE:
                raise HTTPException(
                    status_code=422,
                    detail="Unsupported site URL",
                )
            raise HTTPException(
                status_code=422,
                detail=(
                    "Invalid Telegram source. Use @username or "
                    "https://t.me/<username>"
                ),
            )

        if source_type == SourceType.TELEGRAM and isinstance(
            parser, TelegramParser
        ):
            username = parser.normalize_username(url)
            return f"https://t.me/{username}"

        return url.strip()

    @staticmethod
    def list(session: Session) -> list[Source]:
        return session.exec(select(Source)).all()

    @staticmethod
    def list_enabled(session: Session) -> list[Source]:
        return session.exec(
            select(Source).where(Source.enabled.is_(True))
        ).all()

    @staticmethod
    def get(session: Session, source_id: UUID) -> Source:
        source = session.get(Source, source_id)
        if source is None:
            raise HTTPException(status_code=404, detail="Source not found")
        return source

    @staticmethod
    def create(session: Session, source: SourceWrite) -> Source:
        normalized_url = SourceService.validate_and_normalize_url(
            source.type, source.url
        )
        data = source.model_dump()
        data["url"] = normalized_url
        db_source = Source(**data)
        session.add(db_source)
        session.commit()
        return db_source

    @staticmethod
    def update(session: Session, source_id: UUID,
               source: SourceUpdate) -> Source:
        logger.info(f"Updating source {source_id} with data: {source}")
        data = source.model_dump(exclude_unset=True)
        to_change = SourceService.get(session, source_id)

        if "type" in data or "url" in data:
            next_type = data.get("type", to_change.type)
            next_url = data.get("url", to_change.url)
            data["url"] = SourceService.validate_and_normalize_url(
                next_type, next_url
            )

        to_change.sqlmodel_update(data)
        session.add(to_change)
        session.commit()
        session.refresh(to_change)
        return to_change

    @staticmethod
    def delete(session: Session, source_id: UUID) -> None:
        source = SourceService.get(session, source_id)
        has_news_items = session.exec(
            select(NewsItem.id).where(NewsItem.source_id == source.id)
        ).first()
        if has_news_items is not None:
            raise HTTPException(
                status_code=409,
                detail=(
                    "Cannot delete a source with news items; "
                    "set enabled to false instead"
                ),
            )
        session.delete(source)
        session.commit()
