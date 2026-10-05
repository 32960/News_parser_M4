import logging

from sqlmodel import Session, select

from app.api.schemas import NewsItemRead
from app.models import NewsItem

logger = logging.getLogger(__name__)


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
