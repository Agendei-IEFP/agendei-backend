from celery import Celery
from app.core.config import settings

# 1) Criar o Celery app
celery = Celery(
    main="notifications",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["app.worker.tasks"],
)

# 2) Configurações gerais
celery.conf.update(
    task_serializer="json",
    result_expires=3600,
    timezone="UTC",
    enable_utc=True,
)

# 3) Importar o beat_schedule (só agora!)
from app.worker.beat_schedule import beat_schedule

# 4) Aplicar o beat_schedule
celery.conf.beat_schedule = beat_schedule
