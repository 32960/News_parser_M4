import logging
from uuid import UUID

from fastapi import HTTPException
from sqlmodel import Session, select

from app.api.schemas import PostRead
from app.models import Post, PostStatus

logger = logging.getLogger(__name__)

class PostService:
    @staticmethod
    def list(session: Session,
             status: PostStatus | None = None) \
            -> list[PostRead]:
        if status:
            return session.exec(select(Post).where(Post.status == status)).all()
        return session.exec(select(Post)).all()

    @staticmethod
    def get(session: Session, post_id: UUID) -> Post:
        post = session.get(Post, post_id)
        if post is None:
            logger.warning(f"Post not found: {post_id}")
            raise HTTPException(status_code=404, detail="Post not found")
        return post
