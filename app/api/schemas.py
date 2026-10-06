from __future__ import annotations

from datetime import datetime

from uuid import UUID

from pydantic import field_validator, model_validator
from sqlmodel import Field, SQLModel
from app.models import SourceType, PostStatus


class ErrorResponse(SQLModel):
    detail: str


class SourceRead(SQLModel):
    id: UUID
    type: SourceType
    name: str
    url: str
    enabled: bool


class SourceWrite(SQLModel):
    type: SourceType
    name: str = Field(min_length=1, max_length=255)
    url: str = Field(min_length=1)
    enabled: bool

    @field_validator("name", "url")
    @classmethod
    def strip_non_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Field must not be blank")
        return value


class SourceUpdate(SQLModel):
    type: SourceType | None = None
    name: str | None = Field(default=None, min_length=1, max_length=255)
    url: str | None = Field(default=None, min_length=1)
    enabled: bool | None = None


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
    def strip_non_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Field must not be blank")
        return value


class NewsItemRead(SQLModel):
    id: UUID
    title: str
    summary: str | None = None
    url: str | None = None
    source_id: UUID
    published_at: datetime | None = None
    collected_at: datetime
    telegram_channel_id: int | None = None
    telegram_message_id: int | None = None
    raw_text: str


class PostRead(SQLModel):
    id: UUID
    news_item: NewsItemRead
    generated_text: str | None = None
    generated_at: datetime | None = None
    published_at: datetime | None = None
    status: PostStatus


class TaskResponse(SQLModel):
    id: UUID


class ParseResponse(SQLModel):
    task_id: UUID


class GenerateResponse(SQLModel):
    post_id: UUID


class GeneratePayload(SQLModel):
    news_id: UUID
