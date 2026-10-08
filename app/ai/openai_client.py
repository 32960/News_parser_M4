from __future__ import annotations

import logging

from openai import OpenAI, OpenAIError, RateLimitError

from app.config import get_settings
from app.models import NewsItem

settings = get_settings()
logger = logging.getLogger(__name__)

# Prompt = instructions for the AI model (what kind of post we want)
GENERATE_TEXT_PROMPT = (
    "Сделай короткий и понятный пост для Telegram-канала по новости ниже. "
    "Пиши живым, естественным языком, избегай канцеляризмов и сложных терминов. "
    "Начни с самого важного или неожиданного факта из новости, чтобы зацепить читателя. "
    "Передай только суть исходного текста, не добавляй выдуманные факты. "
    "Уместно используй emoji и закончи мягким приглашением к обсуждению "
    "(например, вопрос читателям)."
)


def get_openai_client() -> OpenAI:
    if not settings.openai_api_key:
        raise ValueError("OpenAI API key not configured")
    return OpenAI(
        api_key=settings.openai_api_key.get_secret_value(),
    )


def text_for_generation(news: NewsItem) -> str:
    """
    Spec rule: send non-empty summary to AI if the source gave one,
    otherwise send raw_text.
    """
    summary = (news.summary or "").strip()
    if summary:
        return summary
    return (news.raw_text or "").strip()


def generate_text(text: str) -> str:
    """
    Call OpenAI and return non-empty post text.
    Raises on API errors or empty model output (so Celery can mark generation_failed).
    """
    if not text or not text.strip():
        raise ValueError("Empty text passed to AI generation")

    try:
        with get_openai_client() as client:
            response = client.responses.create(
                model=settings.openai_model,
                instructions=GENERATE_TEXT_PROMPT,
                input=text,
            )
            output = (response.output_text or "").strip()
            if not output:
                raise ValueError("AI returned empty text")
            return output
    except RateLimitError:
        # Rate limit = too many requests to OpenAI in a short time (HTTP 429)
        logger.error("OpenAI rate limit exceeded while generating a post")
        raise
    except (ValueError, OpenAIError) as exc:
        # Do not log secrets (API key). Only the error type/message from the SDK.
        logger.error("Failed to generate text: %s", exc)
        raise
