from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from telethon import TelegramClient

from app.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)


def get_telegram_client() -> TelegramClient:
    return TelegramClient(
        settings.telegram_session_path,
        api_id=settings.telegram_api_id,
        api_hash=settings.telegram_api_hash,
    )


@asynccontextmanager
async def get_authorized_client() -> AsyncIterator[TelegramClient]:
    """
    Open saved Telegram session for background jobs.

    Important: do NOT call client.start() here — that would ask for phone/code
    inside a Celery worker. Authorize once with:
        python -m app.telegram.authorize
    """
    client = get_telegram_client()
    try:
        await client.connect()
        if not await client.is_user_authorized():
            logger.error(
                "Telegram session is not authorized. "
                "Run: python -m app.telegram.authorize"
            )
            raise RuntimeError(
                "Telegram session is not authorized. "
                "Run: python -m app.telegram.authorize"
            )
        yield client
    finally:
        logger.info("Disconnecting Telegram client")
        await client.disconnect()


def authorize() -> None:
    """Interactive login (phone + code). Only for local/manual run."""
    client = get_telegram_client()
    logger.info("Starting interactive Telegram authorization...")
    client.start()
    logger.info(
        "Authorization OK. Session saved to %s",
        settings.telegram_session_path,
    )


async def send_message_to_channel(message: str) -> None:
    channel = (settings.telegram_target_channel or "").strip()
    if not channel:
        # Must raise: caller marks post as publication_failed
        raise RuntimeError("TELEGRAM_TARGET_CHANNEL is not configured")

    async with get_authorized_client() as client:
        await client.send_message(channel, message)
        logger.info("Message sent to Telegram channel %s", channel)
