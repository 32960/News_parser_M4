import logging
import asyncio
from app.db import open_session
from app.models import Source
from app.parsers import get_parser
from app.services import SourceService, NewsService
from celery_app import app

logger = logging.getLogger(__name__)

@app.task
def parse_sources():
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
            except Exception:
                session.rollback()
                logger.exception("Failed to parse source %s", source_id)

        logger.info(f"Parsed {total_parsed} articles")
    return total_parsed


@app.task
def generate_post(news_id):
    logger.info(f"Generating post for news {news_id}...")
    pass


@app.task
def publish_post(post_id):
    logger.info(f"Publishing post {post_id}...")
    pass


@app.task
def publish_next_post():
    logger.info("Publishing next ready post...")
    pass
