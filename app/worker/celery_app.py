from celery import Celery
from app.core.config import settings

# Criar o Celery app
celery = Celery(
    main="notifications",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["app.worker.tasks"],
)

# Configurações gerais
celery.conf.update(
    task_serializer="json",
    result_expires=3600,
    timezone="UTC",
    enable_utc=True,
)

# Importar o beat_schedule
from app.worker.beat_schedule import beat_schedule

# Aplicar o beat_schedule
celery.conf.beat_schedule = beat_schedule
