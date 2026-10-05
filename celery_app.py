from datetime import timedelta

from celery import Celery
from celery.schedules import crontab
from app.config import get_settings
import logging


settings = get_settings()
logger = logging.getLogger(__name__)


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

    beat_schedule={
        'run-every-30-minutes': {
            'task': 'app.tasks.parse_sources',
            'schedule': timedelta(minutes=30),
        },
        'publish-every-half-hour': {
            'task': 'app.tasks.publish_next_post',
            'schedule': crontab(minute="0,30"),
        },
    }
)

logger.info("Celery app initialized")
