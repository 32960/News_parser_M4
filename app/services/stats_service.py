from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from uuid import UUID

from sqlmodel import Session, col, func, select

from app.api.schemas import SourceStatsRead, StatsRead
from app.models import NewsItem, Post, PostStatus, Source


class StatsService:
    @staticmethod
    def get(session: Session) -> StatsRead:
        """
        Operational stats for the editor dashboard (bonus).

        - collected / generated / published from DB counts
        - errors = generation_failed + publication_failed
        - per source: news count, last successful collection
          (max news.collected_at), error breakdown
        """
        news_total = session.exec(
            select(func.count()).select_from(NewsItem)
        ).one()

        status_counts = {
            status: 0 for status in PostStatus
        }
        for status, count in session.exec(
            select(Post.status, func.count())
            .group_by(Post.status)
        ).all():
            status_counts[status] = count

        generated = (
            status_counts[PostStatus.GENERATED]
            + status_counts[PostStatus.PUBLISHED]
        )
        published = status_counts[PostStatus.PUBLISHED]
        generation_failed = status_counts[PostStatus.GENERATION_FAILED]
        publication_failed = status_counts[PostStatus.PUBLICATION_FAILED]

        news_agg: dict[UUID, tuple[int, datetime | None]] = {}
        for source_id, count, last_at in session.exec(
            select(
                NewsItem.source_id,
                func.count(),
                func.max(NewsItem.collected_at),
            ).group_by(NewsItem.source_id)
        ).all():
            news_agg[source_id] = (count, last_at)

        post_agg: dict[UUID, dict[PostStatus, int]] = defaultdict(
            lambda: {status: 0 for status in PostStatus}
        )
        for source_id, status, count in session.exec(
            select(NewsItem.source_id, Post.status, func.count())
            .join(Post, col(Post.news_item_id) == col(NewsItem.id))
            .group_by(NewsItem.source_id, Post.status)
        ).all():
            post_agg[source_id][status] = count

        sources = session.exec(
            select(Source).order_by(col(Source.name))
        ).all()
        source_stats: list[SourceStatsRead] = []
        for source in sources:
            news_count, last_collected_at = news_agg.get(
                source.id, (0, None)
            )
            posts = post_agg[source.id]
            source_stats.append(
                SourceStatsRead(
                    id=source.id,
                    name=source.name,
                    enabled=source.enabled,
                    news_count=news_count,
                    last_successful_collection_at=last_collected_at,
                    generated=(
                        posts[PostStatus.GENERATED]
                        + posts[PostStatus.PUBLISHED]
                    ),
                    published=posts[PostStatus.PUBLISHED],
                    generation_failed=posts[PostStatus.GENERATION_FAILED],
                    publication_failed=posts[PostStatus.PUBLICATION_FAILED],
                )
            )

        return StatsRead(
            collected=news_total,
            generated=generated,
            published=published,
            generation_failed=generation_failed,
            publication_failed=publication_failed,
            sources=source_stats,
        )
