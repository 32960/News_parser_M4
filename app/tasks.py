from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from uuid import UUID

from sqlmodel import Session

from app.ai.openai_client import generate_text
from app.db import open_session
from app.models import Source, Post, PostStatus, NewsItem
from app.parsers import get_parser
from app.services.news_service import NewsService
from app.services.post_service import PostService
from app.services.source_service import SourceService
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
                    logger.warning(f"Parser not found for source: {source}")
                    continue
                articles = asyncio.run(parser.parse(source.url))
                if not articles:
                    logger.warning(f"No new articles for : {source}")
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

        logger.info(f"Parsed {total_parsed} articles")
    return total_parsed


def start_generating(session: Session, news_id: UUID):
    news = session.get(NewsItem, news_id)
    if not news:
        logger.warning(f"News not found: {news_id}")
        return None
    if not news.source.enabled:
        logger.warning(f"Source not enabled: {news.source.id}")
        return None
    if not news.raw_text.strip():
        logger.warning(f"News has no raw text: {news_id}")
        return None
    post = Post(news_item_id=news_id)
    session.add(post)
    session.commit()
    logger.info(f"Created new post {post.id} for news {news_id}")
    generate_post.delay(str(post.id))
    return post.id


@app.task
def generate_post(post_id: str | UUID) -> str | None:
    logger.info(f"Generating text for {post_id}...")
    with open_session() as session:
        post = session.get(Post, UUID(str(post_id)))
        if not post:
            logger.warning(f"Post not found: {post_id}")
            return None
        if post.status not in (PostStatus.NEW, PostStatus.GENERATION_FAILED):
            logger.warning(f"Text for this post cannot be generated: {post_id}")
            return None
        news = session.get(NewsItem, post.news_item_id)
        if not news:
            logger.warning("News not found for post %s", post_id)
            return None
        source = session.get(Source, news.source_id)
        if not source or not source.enabled:
            logger.info("Source disabled for post %s; skipping generation", post_id)
            return None
        if not news.raw_text or not news.raw_text.strip():
            logger.warning("News has no raw text for post %s", post_id)
            return None
        try:
            text = generate_text(news.raw_text)
            post.generated_text = text
            post.generated_at = datetime.now()
            post.status = PostStatus.GENERATED
            session.add(post)
            session.commit()
        except Exception:
            post.status = PostStatus.GENERATION_FAILED
            session.add(post)
            session.commit()
            logger.exception(f"Failed to generate text for post {post_id}")
            return None

        return str(post.id)


@app.task
def publish_post(post_id):
    logger.info(f"Publishing post {post_id}...")
    pass


@app.task
def publish_next_post():
    logger.info("Publishing next ready post...")
    pass
