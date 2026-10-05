from __future__ import annotations

from datetime import datetime

from app.models import SourceType
from app.parsers.base_parser import BaseParser
from app.telegram.client import get_authorized_client


class TelegramParser(BaseParser):
    source_type = SourceType.TELEGRAM
    telegram_prefixes = ['t.me', 'https://t.me', 'http://t.me', '@']

    def can_handle(self, url: str) -> bool:
        return any(url.startswith(prefix) for prefix in self.telegram_prefixes)

    def normalize_username(self, url):
        # TODO
        # t.me/username -> username
        # @username -> username
        # https://t.me/username -> username
        # http://t.me/username -> username
        return url

    async def parse(self, url: str, limit: int = 10) -> list[dict]:
        async with get_authorized_client() as client:
            channel = await client.get_entity(url)
            articles = []
            async for message in client.iter_messages(channel, limit=limit):
                article = self.parse_message(message)
                if article:
                    articles.append(article)
            return articles

    def parse_message(self, message) -> dict | None:
        text = message.text
        stripped_text = (text or '').strip()
        if not stripped_text:
            return None

        title = stripped_text.splitlines()[0].strip()[:200]
        return {
            'title': title,
            'raw_text': text,
            'telegram_message_id': message.id,
            'telegram_channel_id': message.chat_id,
            'collected_at': datetime.now()
        }
