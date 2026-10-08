from __future__ import annotations

import logging
import re

from app.models import SourceType
from app.parsers.base_parser import BaseParser
from app.telegram.client import get_authorized_client
from app.utils import as_utc, title_from_text, utc_now

logger = logging.getLogger(__name__)

# Public Telegram username: letters, digits, underscore; length 5..32
_USERNAME_RE = re.compile(r"^[A-Za-z0-9_]{5,32}$")


class TelegramParser(BaseParser):
    source_type = SourceType.TELEGRAM

    def can_handle(self, url: str) -> bool:
        """Accept @name, t.me/name, https://t.me/name, or bare username."""
        try:
            self.normalize_username(url)
            return True
        except ValueError:
            return False

    def normalize_username(self, url: str) -> str:
        """
        Turn different user inputs into a plain channel username.

        Examples:
          @durov             -> durov
          t.me/durov         -> durov
          https://t.me/durov -> durov
          durov              -> durov
        """
        value = (url or "").strip()
        if not value:
            raise ValueError("Telegram URL is empty")

        lower = value.lower()
        for prefix in ("https://t.me/", "http://t.me/", "t.me/"):
            if lower.startswith(prefix):
                value = value[len(prefix) :]
                break

        if value.startswith("@"):
            value = value[1:]

        # Drop path/query leftovers: "name/123", "s/name", "name?start=1"
        parts = value.split("?")[0].split("/")
        if parts and parts[0].lower() == "s" and len(parts) > 1:
            value = parts[1]
        else:
            value = parts[0] if parts else ""
        value = value.strip()

        if not _USERNAME_RE.fullmatch(value):
            raise ValueError(f"Invalid Telegram username: {url!r}")

        return value

    async def parse(self, url: str, limit: int = 10) -> list[dict]:
        username = self.normalize_username(url)

        async with get_authorized_client() as client:
            channel = await client.get_entity(username)
            articles: list[dict] = []

            async for message in client.iter_messages(channel, limit=limit):
                article = self.parse_message(message, channel_username=username)
                if article:
                    articles.append(article)

            logger.info(
                "Telegram parser collected %s messages from @%s",
                len(articles),
                username,
            )
            return articles

    def parse_message(
        self, message, channel_username: str | None = None
    ) -> dict | None:
        # message.text in Telethon = text OR media caption
        text = (message.text or "").strip()
        if not text:
            return None

        channel_id = message.chat_id
        message_id = message.id
        if channel_id is None or message_id is None:
            return None

        # Public link to the original message, if we know the username
        message_url = None
        if channel_username:
            message_url = f"https://t.me/{channel_username}/{message_id}"

        published_at = None
        if message.date is not None:
            published_at = as_utc(message.date)

        return {
            "title": title_from_text(text),
            "raw_text": text,
            "url": message_url,
            "telegram_channel_id": channel_id,
            "telegram_message_id": message_id,
            "summary": None,
            "published_at": published_at,
            "collected_at": utc_now(),
        }
