from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import and_, or_
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, col, select

from app.api.schemas import NewsItemRead
from app.models import NewsItem
from app.utils import as_utc, blank_to_none, detect_text_language, utc_now

logger = logging.getLogger(__name__)


class NewsService:
    @staticmethod
    def list(
        session: Session,
        *,
        q: str | None = None,
        lang: str | None = None,
        max_age_hours: int | None = None,
        source_id: UUID | None = None,
    ) -> list[NewsItemRead]:
        """
        List news with optional global filters (bonus: keywords / lang / age).

        ``q`` — case-insensitive substring in title, summary, or raw_text.
        ``lang`` — ``ru`` / ``en`` (rough detector on title+text).
        ``max_age_hours`` — keep items whose published_at (or collected_at
        if publish time is unknown) is not older than N hours.
        ``source_id`` — only this source.
        """
        stmt = select(NewsItem)

        if source_id is not None:
            stmt = stmt.where(NewsItem.source_id == source_id)

        keyword = blank_to_none(q)
        if keyword is not None:
            pattern = f"%{keyword}%"
            stmt = stmt.where(
                or_(
                    col(NewsItem.title).ilike(pattern),
                    col(NewsItem.raw_text).ilike(pattern),
                    col(NewsItem.summary).ilike(pattern),
                )
            )

        if max_age_hours is not None:
            cutoff = utc_now() - timedelta(hours=max_age_hours)
            stmt = stmt.where(
                or_(
                    NewsItem.published_at >= cutoff,
                    and_(
                        NewsItem.published_at.is_(None),
                        NewsItem.collected_at >= cutoff,
                    ),
                )
            )

        stmt = stmt.order_by(col(NewsItem.collected_at).desc())
        items = list(session.exec(stmt).all())

        lang_code = blank_to_none(lang)
        if lang_code is not None:
            wanted = lang_code.lower()
            items = [
                item
                for item in items
                if detect_text_language(
                    f"{item.title}\n{item.raw_text}"
                )
                == wanted
            ]

        return items

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
