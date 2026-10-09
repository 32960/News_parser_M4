from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import ConfigDict, field_validator, model_validator
from sqlmodel import Field, SQLModel

from app.models import PostStatus, SourceType

# Example UUID for Swagger "Try it out" bodies
_EXAMPLE_UUID = "3fa85f64-5717-4562-b3fc-2c963f66afa6"


class ErrorResponse(SQLModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [{"detail": "Source not found"}]
        }
    )

    detail: str = Field(description="Human-readable error message")


class SourceRead(SQLModel):
    id: UUID = Field(description="Source ID")
    type: SourceType = Field(description="site or telegram")
    name: str = Field(description="Display name")
    url: str = Field(description="Feed URL or Telegram channel link/username")
    enabled: bool = Field(
        description="If false, skipped by collection and AI generation"
    )


class SourceWrite(SQLModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "type": "site",
                    "name": "Habr",
                    "url": "https://habr.com/ru/rss/articles/",
                    "enabled": True,
                },
                {
                    "type": "telegram",
                    "name": "Example channel",
                    "url": "https://t.me/durov",
                    "enabled": True,
                },
            ]
        }
    )

    type: SourceType = Field(
        description="site (needs a built-in parser) or telegram"
    )
    name: str = Field(
        min_length=1,
        max_length=255,
        description="Display name for the source",
    )
    url: str = Field(
        min_length=1,
        description=(
            "For site: supported feed URL. "
            "For telegram: @username or https://t.me/<username>"
        ),
    )
    enabled: bool = Field(
        default=True,
        description="Whether the source is used in collection/generation",
    )

    @field_validator("name", "url")
    @classmethod
    def strip_non_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Field must not be blank")
        return value


class SourceUpdate(SQLModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [{"enabled": False}]
        }
    )

    type: SourceType | None = Field(
        default=None, description="New type (optional)"
    )
    name: str | None = Field(
        default=None, min_length=1, max_length=255, description="New name"
    )
    url: str | None = Field(
        default=None, min_length=1, description="New URL"
    )
    enabled: bool | None = Field(
        default=None,
        description="Set false to stop new collection and generation",
    )

    @model_validator(mode="before")
    @classmethod
    def reject_null_fields(cls, data: object) -> object:
        if isinstance(data, dict):
            for field in ("type", "name", "url", "enabled"):
                if field in data and data[field] is None:
                    raise ValueError(f"{field} cannot be null")
        return data

    @field_validator("name", "url")
    @classmethod
    def strip_non_blank(cls, value: str | None) -> str | None:
        if value is None:
            return value
        value = value.strip()
        if not value:
            raise ValueError("Field must not be blank")
        return value


class NewsItemRead(SQLModel):
    id: UUID
    title: str
    summary: str | None = Field(
        default=None, description="Short summary from source, if any"
    )
    url: str | None = Field(
        default=None, description="Article URL (required for site news)"
    )
    source_id: UUID
    published_at: datetime | None = Field(
        default=None,
        description="Publication time in the source (UTC), if known",
    )
    collected_at: datetime = Field(
        description="When our service collected the news (UTC)"
    )
    telegram_channel_id: int | None = None
    telegram_message_id: int | None = None
    raw_text: str = Field(description="Original text without HTML")


class PostRead(SQLModel):
    id: UUID
    news_item: NewsItemRead
    generated_text: str | None = Field(
        default=None, description="AI text; null until generation succeeds"
    )
    generated_at: datetime | None = Field(
        default=None, description="When AI generation succeeded (UTC)"
    )
    published_at: datetime | None = Field(
        default=None, description="When the post was sent to Telegram (UTC)"
    )
    status: PostStatus = Field(
        description=(
            "new | generated | published | generation_failed | publication_failed"
        )
    )


class ParseResponse(SQLModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [{"task_id": _EXAMPLE_UUID}]
        }
    )

    task_id: UUID = Field(
        description="Celery task id for the collection job"
    )


class GenerateResponse(SQLModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [{"post_id": _EXAMPLE_UUID}]
        }
    )

    post_id: UUID = Field(
        description="Created post id; poll GET /api/posts/{id}/ for status"
    )


class PublishResponse(SQLModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [{"post_id": _EXAMPLE_UUID}]
        }
    )

    post_id: UUID = Field(
        description="Post id queued for Telegram send"
    )


class GeneratePayload(SQLModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [{"news_id": _EXAMPLE_UUID}]
        }
    )

    news_id: UUID = Field(
        description="ID of an existing news item from GET /api/news/"
    )
