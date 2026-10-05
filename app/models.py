from datetime import datetime
from enum import StrEnum, auto
import sqlalchemy as sa
from sqlmodel import SQLModel, Field, Relationship
from uuid import UUID, uuid4


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


class Source(SQLModel, table=True):
    __tablename__ = "sources"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    type: SourceType = (Field(
        sa_column=sa.Column(enum_to_sql_type(SourceType),
                            nullable=False,
                            default=SourceType.SITE
                            )))
    name: str = Field(min_length=1, max_length=255, nullable=False)
    url: str = Field(min_length=1, nullable=False)
    enabled: bool = Field(default=True)

    news_items: list["NewsItem"] = Relationship(back_populates="source")

    def __str__(self):
        return f"{self.type} {self.name}: {self.url}"


class NewsItem(SQLModel, table=True):
    __tablename__ = "news_items"
    __table_args__ = (
        sa.UniqueConstraint("url", name="uq_news_items_url"),
        # sa.UniqueConstraint("telegram_channel_id", "telegram_message_id",
        #                     name="uq_news_items_tg"),
    )

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    title: str = Field(min_length=1, max_length=255, nullable=False)
    url: str | None = Field(default=None, nullable=True)
    telegram_channel_id: int | None = Field(
        default=None, nullable=True, sa_type=sa.BigInteger
    )
    telegram_message_id: int | None = Field(default=None, nullable=True)
    summary: str | None = Field(default=None, nullable=True)
    source_id: UUID = Field(foreign_key="sources.id",
                            ondelete="RESTRICT", nullable=False)
    published_at: datetime | None = Field(default=None, nullable=True)
    collected_at: datetime = Field(default_factory=datetime.now)
    raw_text: str = Field(nullable=False)

    source: Source = Relationship(back_populates="news_items")
    posts: list["Post"] = Relationship(back_populates='news_item')


class Post(SQLModel, table=True):
    __tablename__ = 'posts'

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    news_item_id: UUID = Field(foreign_key='news_items.id',
                               ondelete='RESTRICT', nullable=False)
    generated_text: str = Field(nullable=True)
    generated_at: datetime = Field(default=None, nullable=True)
    published_at: datetime = Field(default=None, nullable=True)
    status: PostStatus = Field(default=PostStatus.NEW, nullable=False)


    news_item: NewsItem = Relationship(back_populates='posts')
