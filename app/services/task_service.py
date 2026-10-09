from __future__ import annotations

import logging
from uuid import UUID

from fastapi import HTTPException
from sqlmodel import Session

from app.api.schemas import (
    GeneratePayload,
    GenerateResponse,
    ParseResponse,
    PublishResponse,
)
from app.models import NewsItem, Post, PostStatus
from app.services.post_service import PostService
from app.tasks import parse_sources, publish_post, start_generating

logger = logging.getLogger(__name__)


class TaskService:
    @staticmethod
    def parse() -> ParseResponse:
        # Celery task id is a UUID string — API returns it as task_id
        task = parse_sources.delay()
        return ParseResponse(task_id=UUID(str(task.id)))

    @staticmethod
    def generate(session: Session, payload: GeneratePayload) -> GenerateResponse:
        post_id = start_generating(session, payload.news_id)
        if post_id is None:
            news = session.get(NewsItem, payload.news_id)
            if news is None:
                raise HTTPException(status_code=404, detail="News not found")
            if not news.source.enabled:
                raise HTTPException(
                    status_code=409,
                    detail="Source is disabled",
                )
            raise HTTPException(
                status_code=409,
                detail="News has no text for generation",
            )
        return GenerateResponse(post_id=post_id)

    @staticmethod
    def publish(
        session: Session, post_id: UUID
    ) -> tuple[Post, bool]:
        """
        Prepare manual publish.

        Returns:
            (post, queued)
            - queued=False + status published → API must return HTTP 200 with post
            - queued=True → Celery task started, API returns HTTP 202 + post_id
        """
        post = PostService.get(session, post_id)

        if post.status == PostStatus.PUBLISHED:
            logger.info("Post %s already published; return saved result", post_id)
            return post, False

        if post.status in (PostStatus.NEW, PostStatus.GENERATION_FAILED):
            raise HTTPException(
                status_code=409,
                detail="Post has no generated text and cannot be published",
            )

        if post.status not in (
            PostStatus.GENERATED,
            PostStatus.PUBLICATION_FAILED,
        ):
            raise HTTPException(
                status_code=409,
                detail=f"Post cannot be published (status={post.status})",
            )

        if not post.generated_text or not post.generated_text.strip():
            raise HTTPException(
                status_code=409,
                detail="Post has no generated text and cannot be published",
            )

        publish_post.delay(str(post.id))
        logger.info("Queued publish task for post %s", post.id)
        return post, True

    @staticmethod
    def publish_response(
        session: Session, post_id: UUID
    ) -> tuple[Post | PublishResponse, int]:
        """Return body + HTTP status code for the publish endpoint."""
        post, queued = TaskService.publish(session, post_id)
        if not queued:
            return post, 200
        return PublishResponse(post_id=post.id), 202
