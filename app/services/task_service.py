import logging
from uuid import UUID

from sqlmodel import Session

from app.api.schemas import TaskResponse, GeneratePayload
from app.tasks import parse_sources, publish_post, start_generating

logger = logging.getLogger(__name__)


class TaskService:
    @staticmethod
    def parse(session: Session) -> TaskResponse:
        return TaskResponse(id=parse_sources.delay().id)

    @staticmethod
    def generate(session: Session, payload: GeneratePayload) -> TaskResponse:
        return TaskResponse(
            id=start_generating(session, payload.news_item_id)
        )

    @staticmethod
    def publish(session: Session, post_id: UUID) -> TaskResponse:
        return TaskResponse(id=publish_post.delay(post_id).id)
