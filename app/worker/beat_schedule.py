from celery.schedules import crontab

beat_schedule = {
    # Envio imediato continua a cada 60s
    "dispatch-scheduled-notifications": {
        "task": "app.worker.tasks.dispatch_pending_notifications",
        "schedule": 1.0,
    },

    # Verificação diária às 08:00
    "daily-pending-check": {
        "task": "app.worker.tasks.dispatch_pending_notifications",
        "schedule": crontab( minute="*"),
    },
}
