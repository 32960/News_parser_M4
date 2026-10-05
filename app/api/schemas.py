from __future__ import annotations

from datetime import datetime

from uuid import UUID

from sqlmodel import SQLModel
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
    name: str
    url: str
    enabled: bool


class SourceUpdate(SQLModel):
    type: SourceType | None = None
    name: str | None = None
    url: str | None = None
    enabled: bool | None = None


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


class GeneratePayload(SQLModel):
    news_item_id: UUID
