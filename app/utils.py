import asyncio
from collections.abc import Coroutine
from datetime import datetime, timezone
from typing import TypeVar
from urllib.parse import urlparse

T = TypeVar("T")


def run_async(coro: Coroutine[object, object, T]) -> T:
    """
    Run an async function from sync Celery tasks.

    Always creates a fresh event loop via asyncio.run (safe for Celery prefork).
    """
    return asyncio.run(coro)


def utc_now() -> datetime:
    """Timezone-aware UTC timestamp for DB timestamptz columns."""
    return datetime.now(timezone.utc)


def as_utc(value: datetime) -> datetime:
    """Normalize a datetime to UTC. Naive values are treated as already UTC."""
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def blank_to_none(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


def is_absolute_http_url(url: str | None) -> bool:
    """True only for full http/https links like https://habr.com/...."""
    if not url or not url.strip():
        return False
    parsed = urlparse(url.strip())
    return parsed.scheme in ("http", "https") and bool(parsed.netloc)


def title_from_text(raw_text: str, fallback_title: str | None = None) -> str:
    """
    Build a non-empty title for NewsItem.

    Spec rule: use source title if present; otherwise take the first 200
    characters of the first non-empty line of raw_text (trimmed).
    """
    if fallback_title is not None:
        cleaned = fallback_title.strip()
        if cleaned:
            return cleaned

    for line in raw_text.splitlines():
        cleaned = line.strip()
        if cleaned:
            return cleaned[:200]

    # Last resort: raw_text itself (already required to be non-empty by callers)
    return raw_text.strip()[:200]
