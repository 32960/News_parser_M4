import logging
from uuid import UUID

from fastapi import HTTPException
from sqlmodel import Session

from app.api.schemas import TaskResponse, ParseResponse, GenerateResponse, GeneratePayload
from app.models import NewsItem
from app.tasks import parse_sources, publish_post, start_generating

logger = logging.getLogger(__name__)


class TaskService:
    @staticmethod
    def parse(session: Session) -> ParseResponse:
        return ParseResponse(task_id=parse_sources.delay().id)

    @staticmethod
    def generate(session: Session, payload: GeneratePayload) -> GenerateResponse:
        post_id = start_generating(session, payload.news_id)
        if post_id is None:
            news = session.get(NewsItem, payload.news_id)
            if news is None:
                raise HTTPException(status_code=404, detail="News not found")
            if not news.source.enabled:
                raise HTTPException(status_code=409, detail="Source is disabled")
            raise HTTPException(status_code=409, detail="News has no raw text")
        return GenerateResponse(post_id=post_id)

    @staticmethod
    def publish(session: Session, post_id: UUID) -> TaskResponse:
        return TaskResponse(id=publish_post.delay(post_id).id)
