from uuid import UUID

from fastapi import HTTPException
from sqlmodel import Session, select

from app.api.schemas import SourceUpdate, SourceWrite
from app.models import NewsItem, Source, SourceType
from app.parsers import get_parser


class SourceService:
    @staticmethod
    def validate_site(source_type: SourceType, url: str) -> None:
        if source_type == SourceType.SITE and get_parser(source_type, url) is None:
            raise HTTPException(status_code=422, detail="Unsupported site URL")

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
        SourceService.validate_site(source.type, source.url)
        source = Source(**source.model_dump())
        session.add(source)
        session.commit()
        return source

    @staticmethod
    def update(session: Session, source_id: UUID,
               source: SourceUpdate) -> Source:
        data = source.model_dump(exclude_unset=True)
        to_change = SourceService.get(session, source_id)
        if "type" in data or "url" in data:
            SourceService.validate_site(
                data.get("type", to_change.type), data.get("url", to_change.url)
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
