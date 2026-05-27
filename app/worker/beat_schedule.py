from celery.schedules import crontab
from app.worker.celery_app import celery_app

celery_app.conf.beat_schedule = {
    "dispatch-scheduled-notifications": {
        "task": "app.worker.tasks.dispatch_pending_notifications",
        "schedule": 60.0,  # a cada 60 segundos
    },
}