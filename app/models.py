from datetime import datetime
from enum import StrEnum, auto
from uuid import UUID, uuid4

import sqlalchemy as sa
from sqlmodel import Field, Relationship, SQLModel

from app.utils import utc_now


def enum_to_sql_type(enum_type: type[StrEnum]) -> sa.Enum:
    return sa.Enum(enum_type, values_callable=lambda x: [e.value for e in x])


class SourceType(StrEnum):
    SITE = auto()
    TELEGRAM = auto()


class PostStatus(StrEnum):
    NEW = auto()
    GENERATED = auto()
    PUBLISHED = auto()
    GENERATION_FAILED = auto()
    PUBLICATION_FAILED = auto()


TZDateTime = sa.DateTime(timezone=True)


class Source(SQLModel, table=True):
    __tablename__ = "sources"
    __table_args__ = (
        sa.CheckConstraint("btrim(name) <> ''", name="ck_sources_name_nonempty"),
        sa.CheckConstraint("btrim(url) <> ''", name="ck_sources_url_nonempty"),
    )

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    type: SourceType = Field(
        sa_column=sa.Column(
            enum_to_sql_type(SourceType),
            nullable=False,
            default=SourceType.SITE,
        )
    )
    name: str = Field(min_length=1, max_length=255, nullable=False)
    url: str = Field(min_length=1, nullable=False)
    enabled: bool = Field(default=True, nullable=False)

    news_items: list["NewsItem"] = Relationship(back_populates="source")

    def __str__(self) -> str:
        return f"{self.type} {self.name}: {self.url}"


class NewsItem(SQLModel, table=True):
    __tablename__ = "news_items"
    __table_args__ = (
        # Partial unique indexes: NULL urls/ids (the other source type) must not
        # collide. A plain UNIQUE(url) is not enough for Telegram rows.
        sa.Index(
            "uq_news_items_site_url",
            "url",
            unique=True,
            postgresql_where=sa.text("url IS NOT NULL"),
        ),
        sa.Index(
            "uq_news_items_telegram",
            "telegram_channel_id",
            "telegram_message_id",
            unique=True,
            postgresql_where=sa.text(
                "telegram_channel_id IS NOT NULL AND telegram_message_id IS NOT NULL"
            ),
        ),
        sa.CheckConstraint(
            "btrim(title) <> '' AND btrim(raw_text) <> ''",
            name="ck_news_items_nonempty_text",
        ),
        sa.CheckConstraint(
            "summary IS NULL OR btrim(summary) <> ''",
            name="ck_news_items_summary_null_or_nonempty",
        ),
        sa.CheckConstraint(
            "(telegram_channel_id IS NULL) = (telegram_message_id IS NULL)",
            name="ck_news_items_tg_ids_together",
        ),
        sa.CheckConstraint(
            "telegram_channel_id IS NOT NULL OR url IS NOT NULL",
            name="ck_news_items_has_identity",
        ),
        sa.CheckConstraint(
            "url IS NULL OR url LIKE 'http://%' OR url LIKE 'https://%'",
            name="ck_news_items_url_absolute",
        ),
    )

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    title: str = Field(min_length=1, nullable=False)
    url: str | None = Field(default=None, nullable=True)
    telegram_channel_id: int | None = Field(
        default=None, nullable=True, sa_type=sa.BigInteger
    )
    telegram_message_id: int | None = Field(
        default=None, nullable=True, sa_type=sa.BigInteger
    )
    summary: str | None = Field(default=None, nullable=True)
    source_id: UUID = Field(
        foreign_key="sources.id", ondelete="RESTRICT", nullable=False
    )
    published_at: datetime | None = Field(
        default=None, nullable=True, sa_type=TZDateTime
    )
    collected_at: datetime = Field(
        default_factory=utc_now, nullable=False, sa_type=TZDateTime
    )
    raw_text: str = Field(nullable=False)

    source: Source = Relationship(back_populates="news_items")
    posts: list["Post"] = Relationship(back_populates="news_item")


class Post(SQLModel, table=True):
    __tablename__ = "posts"
    __table_args__ = (
        sa.CheckConstraint(
            "("
            "  status IN ('new', 'generation_failed')"
            "  AND generated_text IS NULL"
            "  AND generated_at IS NULL"
            "  AND published_at IS NULL"
            ") OR ("
            "  status IN ('generated', 'publication_failed')"
            "  AND generated_text IS NOT NULL AND btrim(generated_text) <> ''"
            "  AND generated_at IS NOT NULL"
            "  AND published_at IS NULL"
            ") OR ("
            "  status = 'published'"
            "  AND generated_text IS NOT NULL AND btrim(generated_text) <> ''"
            "  AND generated_at IS NOT NULL"
            "  AND published_at IS NOT NULL"
            ")",
            name="ck_posts_status_fields",
        ),
    )

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    news_item_id: UUID = Field(
        foreign_key="news_items.id", ondelete="RESTRICT", nullable=False
    )
    generated_text: str | None = Field(default=None, nullable=True)
    generated_at: datetime | None = Field(
        default=None, nullable=True, sa_type=TZDateTime
    )
    published_at: datetime | None = Field(
        default=None, nullable=True, sa_type=TZDateTime
    )
    status: PostStatus = Field(
        default=PostStatus.NEW,
        sa_column=sa.Column(
            enum_to_sql_type(PostStatus),
            nullable=False,
            default=PostStatus.NEW,
        ),
    )

    news_item: NewsItem = Relationship(back_populates="posts")
