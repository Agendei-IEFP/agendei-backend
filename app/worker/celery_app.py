from celery import Celery
from app.core.config import settings

celery_app = Celery(
    "notifications",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["app.worker.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    result_expires=3600,
    timezone="UTC",
    enable_utc=True,
)
from app.worker import beat_schedule
