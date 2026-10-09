from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Response, status
from sqlmodel import Session

from app.api.schemas import (
    ErrorResponse,
    GeneratePayload,
    GenerateResponse,
    NewsItemRead,
    ParseResponse,
    PostRead,
    PublishResponse,
    SourceRead,
    SourceUpdate,
    SourceWrite,
)
from app.db import get_session
from app.models import PostStatus
from app.services.news_service import NewsService as n
from app.services.post_service import PostService as p
from app.services.source_service import SourceService as s
from app.services.task_service import TaskService as t

router = APIRouter(prefix="/api", tags=["API"])

SessionDep = Annotated[Session, Depends(get_session)]

ERROR_404 = {404: {"model": ErrorResponse, "description": "Not found"}}
ERROR_409 = {409: {"model": ErrorResponse, "description": "Conflict"}}
ERROR_422 = {
    422: {"model": ErrorResponse, "description": "Validation error"}
}


@router.get(
    "/sources/",
    response_model=list[SourceRead],
    summary="List sources",
    description="Return all news sources (sites and Telegram channels).",
)
async def list_sources(session: SessionDep):
    return s.list(session)


@router.get(
    "/sources/{source_id}/",
    response_model=SourceRead,
    summary="Get source",
    responses=ERROR_404,
)
async def get_source(source_id: UUID, session: SessionDep):
    return s.get(session, source_id)


@router.post(
    "/sources/",
    response_model=SourceRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create source",
    description=(
        "Create a source. For type=site only supported parser URLs are "
        "accepted. For type=telegram use @username or https://t.me/<username>."
    ),
    responses={**ERROR_422},
)
async def create_source(source: SourceWrite, session: SessionDep):
    return s.create(session, source)


@router.patch(
    "/sources/{source_id}/",
    response_model=SourceRead,
    summary="Update source",
    description="Partial update. Use enabled=false to stop new collection/generation.",
    responses={**ERROR_404, **ERROR_422},
)
async def update_source(
    source_id: UUID, source: SourceUpdate, session: SessionDep
):
    return s.update(session, source_id, source)


@router.delete(
    "/sources/{source_id}/",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete source",
    description=(
        "Delete only if the source has no news items. "
        "Otherwise returns 409 — disable it with enabled=false instead."
    ),
    responses={**ERROR_404, **ERROR_409},
)
async def delete_source(source_id: UUID, session: SessionDep):
    s.delete(session, source_id)


@router.get(
    "/news/",
    response_model=list[NewsItemRead],
    summary="List collected news",
)
async def list_news(session: SessionDep):
    return n.list(session)


@router.get(
    "/posts/",
    response_model=list[PostRead],
    summary="List posts",
    description="Optional filter by status, e.g. ?status=generated",
)
async def list_posts(
    session: SessionDep, status: PostStatus | None = None
):
    return p.list(session, status)


@router.get(
    "/posts/{id}/",
    response_model=PostRead,
    summary="Get post",
    description="Return generated text and current status of one post.",
    responses=ERROR_404,
)
async def get_post(id: UUID, session: SessionDep):
    return p.get(session, id)


@router.post(
    "/parse/",
    response_model=ParseResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Start news collection",
    description=(
        "Enqueue Celery task to parse all enabled sources. "
        "Does not wait for parsing to finish. Check GET /api/news/ for results."
    ),
)
async def parse_sources():
    return t.parse()


@router.post(
    "/generate/",
    response_model=GenerateResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Generate post from news",
    description=(
        "Create a new Post (status=new) for the given news_id and enqueue "
        "AI generation. Returns post_id. Disabled source → 409."
    ),
    responses={**ERROR_404, **ERROR_409},
)
async def generate_post(session: SessionDep, payload: GeneratePayload):
    return t.generate(session, payload)


@router.post(
    "/posts/{id}/publish/",
    response_model=PostRead | PublishResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Publish post to Telegram",
    description=(
        "Enqueue send for status generated or publication_failed → 202 + post_id. "
        "If already published → 200 with saved post (no resend). "
        "If no ready text (new / generation_failed) → 409."
    ),
    responses={
        200: {
            "model": PostRead,
            "description": "Already published — return saved post without sending",
        },
        202: {
            "model": PublishResponse,
            "description": "Publish task accepted",
        },
        **ERROR_404,
        **ERROR_409,
    },
)
async def publish_post(
    id: UUID, session: SessionDep, response: Response
):
    body, code = t.publish_response(session, id)
    response.status_code = code
    return body
