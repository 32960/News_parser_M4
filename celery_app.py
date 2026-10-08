from datetime import timedelta
import logging

from celery import Celery
from celery.schedules import crontab

from app.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)

# Queue name for tasks that open the Telethon session file
TELEGRAM_QUEUE = "telegram"

app = Celery("ainews",
             broker=settings.celery_broker_url,
             backend=settings.celery_result_backend,
             include=["app.tasks"])

app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    # One Telethon session file cannot be used by two clients at once.
    # These tasks go to queue "telegram"; run a worker with concurrency=1.
    task_routes={
        "app.tasks.parse_sources": {"queue": TELEGRAM_QUEUE},
        "app.tasks.publish_post": {"queue": TELEGRAM_QUEUE},
        "app.tasks.publish_next_post": {"queue": TELEGRAM_QUEUE},
        # AI generation does not touch Telegram session
        "app.tasks.generate_post": {"queue": "celery"},
    },
    beat_schedule={
        'run-every-30-minutes': {
            'task': 'app.tasks.parse_sources',
            'schedule': timedelta(minutes=30),
        },
        'publish-every-half-hour': {
            'task': 'app.tasks.publish_next_post',
            'schedule': crontab(minute="0,30"),
        },
    },
)

logger.info("Celery app initialized")
