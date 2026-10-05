from uuid import UUID

from fastapi import HTTPException
from sqlmodel import Session, select

from app.api.schemas import PostRead
from app.models import Post


class PostService:
    @staticmethod
    def list(session: Session) -> list[PostRead]:
        return session.exec(select(Post)).all()

    @staticmethod
    def get(session: Session, post_id: UUID) -> Post:
        post = session.get(Post, post_id)
        if post is None:
            raise HTTPException(status_code=404, detail="Post not found")
        return post
