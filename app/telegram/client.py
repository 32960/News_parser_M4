from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from telethon import TelegramClient

from app.config import get_settings

settings = get_settings()


def get_telegram_client() -> TelegramClient:
    return TelegramClient(
        settings.telegram_session_name,
        api_id=settings.telegram_api_id,
        api_hash=settings.telegram_api_hash
    )


@asynccontextmanager
async def get_authorized_client() -> AsyncIterator[TelegramClient]:
    client = get_telegram_client()
    try:
        await client.connect()
        if not await client.is_user_authorized():
            raise RuntimeError(
                "Telegram session is not authorized. Authorize it before parsing."
            )
        yield client
    finally:
        await client.disconnect()


def authorize():
    client = get_telegram_client()
    client.start()


if __name__ == '__main__':
    authorize()