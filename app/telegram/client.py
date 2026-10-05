from __future__ import annotations

from sqlalchemy.util import await_only
from telethon import TelegramClient

from app.config import get_settings

settings = get_settings()


def get_telegram_client() -> TelegramClient:
    return TelegramClient(
        settings.telegram_session_name,
        api_id=settings.telegram_api_id,
        api_hash=settings.telegram_api_hash
    )


async def get_authorized_client() -> TelegramClient | None:
    client = get_telegram_client()
    await client.connect()

    if not await client.is_user_authorized():
        await client.disconnect()
        return None

    return client


def authorize():
    client = get_telegram_client()
    client.start()


if __name__ == '__main__':
    authorize()