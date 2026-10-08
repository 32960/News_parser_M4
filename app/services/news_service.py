from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app.api.schemas import NewsItemRead
from app.models import NewsItem
from app.utils import as_utc, blank_to_none

logger = logging.getLogger(__name__)


class NewsService:
    @staticmethod
    def list(session: Session) -> list[NewsItemRead]:
        return session.exec(select(NewsItem)).all()

    @staticmethod
    def create(session: Session, article: dict[str, Any]) -> NewsItem | None:
        payload = NewsService._normalize(article)

        if payload.get("url"):
            duplicate = session.exec(
                select(NewsItem.id).where(NewsItem.url == payload["url"])
            ).first()
            if duplicate:
                logger.warning("Duplicate article: %s", payload["url"])
                return None
        else:
            channel_id = payload["telegram_channel_id"]
            message_id = payload["telegram_message_id"]
            duplicate = session.exec(
                select(NewsItem.id).where(
                    NewsItem.telegram_channel_id == channel_id,
                    NewsItem.telegram_message_id == message_id,
                )
            ).first()
            if duplicate:
                logger.warning(
                    "Duplicate Telegram article: channel_id=%s, message_id=%s",
                    channel_id,
                    message_id,
                )
                return None

        news_item = NewsItem(**payload)
        session.add(news_item)
        try:
            session.commit()
        except IntegrityError:
            session.rollback()
            logger.warning(
                "Duplicate news rejected by database constraint: url=%s "
                "channel_id=%s message_id=%s",
                payload.get("url"),
                payload.get("telegram_channel_id"),
                payload.get("telegram_message_id"),
            )
            return None
        return news_item

    @staticmethod
    def _normalize(article: dict[str, Any]) -> dict[str, Any]:
        payload = dict(article)
        payload["summary"] = blank_to_none(payload.get("summary"))
        payload["url"] = blank_to_none(payload.get("url"))
        payload["raw_text"] = (payload.get("raw_text") or "").strip()
        payload["title"] = (payload.get("title") or "").strip()

        collected_at = payload.get("collected_at")
        if isinstance(collected_at, datetime):
            payload["collected_at"] = as_utc(collected_at)

        published_at = payload.get("published_at")
        if isinstance(published_at, datetime):
            payload["published_at"] = as_utc(published_at)

        return payload
