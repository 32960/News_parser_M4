from __future__ import annotations

from openai import OpenAI, OpenAIError

from app.config import get_settings
import logging

settings = get_settings()
logger = logging.getLogger(__name__)
GENERATE_TEXT_PROMPT = "Сделай краткое, интересное описание новости для публикации в Telegram-канале, добавь emoji, call to action"


def get_openai_client() -> OpenAI:
    if not settings.openai_api_key:
        raise ValueError("OpenAI API key not configured")
    return OpenAI(
        api_key=settings.openai_api_key,
    )


def generate_text(text: str) -> str | None:
    try:
        with get_openai_client() as client:
            response = client.responses.create(
                model=settings.openai_model,
                instructions=GENERATE_TEXT_PROMPT,
                input=text,
            )
            return response.output_text
    except (ValueError, OpenAIError) as e:
        logger.error(f"Failed to generate text: {str(e)}")
        return None
