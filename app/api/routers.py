from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import delete
from sqlmodel import Session

from app.api.schemas import SourceRead, SourceWrite, SourceUpdate, NewsItemRead, \
    PostRead, TaskResponse, ParseResponse, GenerateResponse, GeneratePayload
from app.db import get_session
from app.models import PostStatus, Post, NewsItem
from app.services.news_service import NewsService as n
from app.services.post_service import PostService as p
from app.services.source_service import SourceService as s
from app.services.task_service import TaskService as t

router = APIRouter(
    prefix="/api",
    tags=["v1"],
    responses={404: {"description": "Not found"}}
)

SessionDep = Annotated[Session, Depends(get_session)]


@router.get("/sources/", response_model=list[SourceRead])
async def list_sources(session: SessionDep):
    return s.list(session)


@router.get("/sources/{source_id}/", response_model=SourceRead,
            responses={404: {"description": "Not found"}})
async def get_source(source_id: UUID, session: SessionDep):
    return s.get(session, source_id)


@router.post("/sources/", response_model=SourceRead,
             status_code=201, responses={400: {"description": "Invalid data"}})
async def create_source(source: SourceWrite, session: SessionDep):
    return s.create(session, source)


@router.patch("/sources/{source_id}/", response_model=SourceRead,
              responses={404: {"description": "Not found"}})
async def update_source(source_id: UUID, source: SourceUpdate,
                        session: SessionDep):
    return s.update(session, source_id, source)


@router.delete("/sources/{source_id}/", status_code=204,
               responses={
                   404: {"description": "Not found"},
                   409: {"description": "Source has news items"},
               }
               )
async def delete_source(source_id: UUID, session: SessionDep):
    s.delete(session, source_id)


@router.get("/news/", response_model=list[NewsItemRead])
async def list_news(session: SessionDep):
    return n.list(session)


@router.get("/posts/", response_model=list[PostRead])
async def list_posts(session: SessionDep, status: PostStatus | None = None):
    return p.list(session, status)


@router.get("/posts/{id}/", response_model=PostRead)
async def get_post(id: UUID, session: SessionDep):
    return p.get(session, id)


@router.post("/parse/", response_model=ParseResponse, status_code=202)
async def parse_sources():
    return t.parse()


@router.post("/generate/", response_model=GenerateResponse, status_code=202)
async def generate_post(session: SessionDep, payload: GeneratePayload):
    return t.generate(session, payload)


@router.post("/posts/{id}/publish/", response_model=TaskResponse, status_code=202)
async def publish_post(id: UUID):
    return t.publish(id)


@router.post('/data/clear/', status_code=204)
async def clear_data(session: SessionDep):
    stmt = delete(Post)
    stmt2 = delete(NewsItem)

    session.exec(stmt)
    session.exec(stmt2)
    session.commit()
