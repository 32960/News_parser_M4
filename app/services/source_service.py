from uuid import UUID

from fastapi import HTTPException
from sqlmodel import Session, select

from app.api.schemas import SourceUpdate, SourceWrite
from app.models import NewsItem, Source


class SourceService:
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
        # check url
        # check if parser exists
        source = Source(**source.model_dump())
        session.add(source)
        session.commit()
        return source

    @staticmethod
    def update(session: Session, source_id: UUID,
               source: SourceUpdate) -> Source:
        # possible 404
        data = source.model_dump(exclude_unset=True)
        to_change = SourceService.get(session, source_id)
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
