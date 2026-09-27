from celery_app import app
import logging

logger = logging.getLogger(__name__)

@app.task
def parse_sources():
    logger.info("Parsing sources...")
    pass


@app.task
def generate_post(news_id):
    logger.info(f"Generating post for news {news_id}...")
    pass


@app.task
def publish_post(post_id):
    logger.info(f"Publishing post {post_id}...")
    pass
