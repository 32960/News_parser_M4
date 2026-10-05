from uuid import UUID

from sqlmodel import Session, select, func, delete, update, insert, exists

from app.api.schemas import SourceRead, SourceWrite, NewsItemRead, PostRead, TaskResponse, GeneratePayload, SourceUpdate
from app.models import Source, NewsItem, Post
from app.tasks import parse_sources, generate_post, publish_post

class SourceService:
    @staticmethod
    def list(session: Session) -> list[Source]:
        # filter logic ??
        return session.exec(select(Source)).all()

    @staticmethod
    def get(session: Session, source_id: UUID) -> Source:
        # possible not found
        return session.exec(select(Source).where(Source.id == source_id)).one()

    @staticmethod
    def create(session: Session, source: SourceWrite) -> Source:
        # check url
        source = Source(**source.model_dump())
        session.add(source)
        session.commit()
        return source

    @staticmethod
    def update(session: Session, source_id: UUID,
               source: SourceUpdate) -> Source:
        # possible 404
        data = source.model_dump(exclude_unset=True)
        to_change = SourceService.get(session, source_id)
        to_change.sqlmodel_update(data)
        session.add(to_change)
        session.commit()
        session.refresh(to_change)
        return to_change

    @staticmethod
    def delete(session, source_id):
        source = SourceService.get(session, source_id)
        session.delete(source)
        session.commit()


class NewsService:
    @staticmethod
    def list(session: Session) -> list[NewsItemRead]:
        return session.exec(select(NewsItem)).all()


class PostService:
    @staticmethod
    def list(session: Session) -> list[PostRead]:
        return session.exec(select(Post)).all()


class TaskService:
    @staticmethod
    def parse(session: Session) -> TaskResponse:
        return TaskResponse(id=parse_sources.delay().id)

    @staticmethod
    def generate(session: Session, payload: GeneratePayload) -> TaskResponse:
        return TaskResponse(
            id=generate_post.delay(news_id=payload.news_item_id).id)

    @staticmethod
    def publish(session: Session, post_id: UUID) -> TaskResponse:
        return TaskResponse(id=publish_post.delay(post_id).id)
