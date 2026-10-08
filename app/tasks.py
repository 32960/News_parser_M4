from __future__ import annotations

import asyncio
import logging
from uuid import UUID

from sqlmodel import Session, select

from app.ai.openai_client import generate_text, text_for_generation
from app.db import open_session
from app.models import Source, Post, PostStatus, NewsItem
from app.parsers import get_parser
from app.services.news_service import NewsService
from app.services.source_service import SourceService
from app.telegram.client import send_message_to_channel
from app.utils import utc_now
from celery_app import app

logger = logging.getLogger(__name__)


@app.task
def parse_sources() -> int:
    logger.info("Parsing sources...")
    with open_session() as session:
        sources: list[Source] = SourceService.list_enabled(session)
        total_parsed = 0
        for source in sources:
            source_id = source.id
            try:
                parser = get_parser(source.type, source.url)
                if not parser:
                    logger.warning("Parser not found for source: %s", source)
                    continue
                articles = asyncio.run(parser.parse(source.url))
                if not articles:
                    logger.warning("No new articles for : %s", source)
                    continue
                for article in articles:
                    # NewsItemCreate pydantic model
                    article['source_id'] = source_id
                    item = NewsService.create(session, article)
                    if item:
                        total_parsed += 1
                        start_generating(session, item.id)
            except Exception:
                session.rollback()
                logger.exception("Failed to parse source %s", source_id)

        logger.info("Parsed %s articles", total_parsed)
    return total_parsed


def start_generating(session: Session, news_id: UUID):
    """
    Create a NEW Post (status=new) and enqueue AI generation.
    Used after collecting news and for manual POST /api/generate/.
    Each call creates a separate post (another AI variant is allowed).
    """
    news = session.get(NewsItem, news_id)
    if not news:
        logger.warning("News not found: %s", news_id)
        return None
    if not news.source.enabled:
        # Do not create a Post and do not call OpenAI
        logger.warning("Source not enabled: %s", news.source.id)
        return None
    if not text_for_generation(news):
        logger.warning("News has no text for AI generation: %s", news_id)
        return None

    post = Post(news_item_id=news_id)
    session.add(post)
    session.commit()
    logger.info("Created new post %s for news %s", post.id, news_id)
    generate_post.delay(str(post.id))
    return post.id


@app.task
def generate_post(post_id: str | UUID) -> str | None:
    logger.info("Generating text for post %s...", post_id)
    with open_session() as session:
        post = session.get(Post, UUID(str(post_id)))
        if not post:
            logger.warning("Post not found: %s", post_id)
            return None
        if post.status not in (PostStatus.NEW, PostStatus.GENERATION_FAILED):
            logger.warning(
                "Text for post %s cannot be generated (status=%s)",
                post_id,
                post.status,
            )
            return None

        news = session.get(NewsItem, post.news_item_id)
        if not news:
            logger.warning("News not found for post %s", post_id)
            return None

        # Re-check right before AI call: disabled source must not spend API money
        source = session.get(Source, news.source_id)
        if not source or not source.enabled:
            logger.info(
                "Source disabled for post %s; skip AI call without changing status",
                post_id,
            )
            return None

        ai_input = text_for_generation(news)
        if not ai_input:
            logger.warning(
                "News %s for post %s has no summary/raw_text for AI",
                news.id,
                post_id,
            )
            return None

        try:
            text = generate_text(ai_input)
            post.generated_text = text
            post.generated_at = utc_now()
            post.status = PostStatus.GENERATED
            session.add(post)
            session.commit()
            logger.info("Generated text for post %s", post_id)
        except Exception:
            session.rollback()
            post = session.get(Post, UUID(str(post_id)))
            if post:
                # Spec: generation_failed => text and both dates are NULL
                post.status = PostStatus.GENERATION_FAILED
                post.generated_text = None
                post.generated_at = None
                post.published_at = None
                session.add(post)
                session.commit()
            logger.exception("Failed to generate text for post %s", post_id)
            return None

        return str(post.id)


@app.task
def publish_post(post_id):
    logger.info("Publishing post %s...", post_id)
    return _publish_post(post_id)


@app.task
def publish_next_post() -> UUID | None:
    logger.info("Publishing next ready post...")
    with open_session() as session:
        post = session.exec(
            select(Post).where(Post.status == PostStatus.GENERATED)
            .order_by(Post.generated_at)
        ).first()
        if not post:
            logger.info("No ready posts to publish")
            return None
        return _publish_post(post.id)


def _publish_post(post_id) -> UUID | None:
    with open_session() as session:
        post = session.get(Post, UUID(str(post_id)))
        if not prepublish_validate(post):
            return None
        try:
            asyncio.run(
                send_message_to_channel(
                    f'{post.generated_text}\n\n{post.news_item.url}'
                )
            )
            post.status = PostStatus.PUBLISHED
            post.published_at = utc_now()
            session.add(post)
            session.commit()
            return post_id
        except Exception:
            session.rollback()
            post = session.get(Post, UUID(str(post_id)))
            if post:
                post.status = PostStatus.PUBLICATION_FAILED
                post.published_at = None
                session.add(post)
                session.commit()
            logger.exception("Failed to publish post %s", post_id)
            return None


def prepublish_validate(post):
    if not post:
        logger.warning("Post not found: %s", post.id)
        return None
    if post.status not in (PostStatus.GENERATED, PostStatus.PUBLICATION_FAILED):
        logger.warning("Post cannot be published: %s", post.id)
        return None
    if not post.generated_text.strip():
        logger.warning("Post has no generated text: %s", post.id)
        return None
    if not post.news_item.url:
        logger.warning("News item has no URL: %s", post.id)
        return None
    if not post.news_item.source.enabled:
        logger.warning(
            "Source disabled for post %s; skipping publication", post.id)
        return None
    return post
