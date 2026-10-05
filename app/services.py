import logging
from uuid import UUID

from fastapi import HTTPException
from sqlmodel import Session, select

from app.api.schemas import SourceWrite, NewsItemRead, PostRead, SourceUpdate
from app.models import Source, NewsItem, Post

logger = logging.getLogger(__name__)


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


class NewsService:
    @staticmethod
    def list(session: Session) -> list[NewsItemRead]:
        return session.exec(select(NewsItem)).all()

    @staticmethod
    def create(session: Session, article: dict) -> NewsItem:
        if article.get('url'):
            if session.exec(
                select(NewsItem.id).where(NewsItem.url == article['url'])
            ).first():
                logger.warning(f"Duplicate article: {article['url']}")
                return None
        else:
            channel_id = article['telegram_channel_id']
            message_id = article['telegram_message_id']
            if session.exec(
                    select(NewsItem.id).where(
                        NewsItem.telegram_channel_id == channel_id,
                        NewsItem.telegram_message_id == message_id)
            ).first():
                logger.warning(
                    "Duplicate Telegram article: channel_id=%s, message_id=%s",
                    channel_id, message_id,
                )
                return None

        news_item = NewsItem(**article)
        session.add(news_item)
        session.commit()
        return news_item

class PostService:
    @staticmethod
    def list(session: Session) -> list[PostRead]:
        return session.exec(select(Post)).all()

    @staticmethod
    def get(session: Session, post_id: UUID) -> Post:
        post = session.get(Post, post_id)
        if post is None:
            raise HTTPException(status_code=404, detail="Post not found")
        return post
