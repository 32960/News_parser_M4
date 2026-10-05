from __future__ import annotations

from datetime import datetime
from app.models import SourceType
from app.parsers.base_parser import BaseParser
from app.telegram.client import get_authorized_client


class TelegramParser(BaseParser):
    source_type = SourceType.TELEGRAM

    def can_handle(self, url: str) -> bool:
        username = self.normalize_username(url)
        return username is not None

    def normalize_username(self, url):
        # TODO
        # t.me/username -> username
        # @username -> username
        # https://t.me/username -> username
        # http://t.me/username -> username
        return url

    async def parse(self, url: str, limit: int = 10) -> list[dict]:
        client = await get_authorized_client()
        channel = client.get_entity(url)
        articles = []
        async for message in client.iter_messages(channel, limit=limit):
            article = self.parse_message(message)
            if article:
                articles.append(article)
        print(articles)
        return articles

    def parse_message(self, message) -> dict | None:
        text = message.text
        return {
            'title': text.splitlines()[0],
            'raw_text': text,
            'message_id': message.id,
            'channel_id': message.chat_id,
            'collected_at': datetime.now()
        }