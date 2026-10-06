from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from telethon import TelegramClient

from app.config import get_settings
import logging

settings = get_settings()
logger = logging.getLogger(__name__)


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
            logger.error("Telegram session is not authorized. Authorize it before parsing.")
            raise RuntimeError(
                "Telegram session is not authorized. Authorize it before parsing."
            )
        yield client
    finally:
        logger.info("Disconnecting from Telegram client.")
        await client.disconnect()


def authorize():
    client = get_telegram_client()
    logger.info("Authorizing Telegram client.")
    client.start()


async def send_message_to_channel(message: str):
    channel = settings.telegram_channel
    if not channel:
        logger.error("Channel is not specified in the config.")
        return
    async with get_authorized_client() as client:
        await client.send_message(channel, message)


if __name__ == '__main__':
    authorize()
