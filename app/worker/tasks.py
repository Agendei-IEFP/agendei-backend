from celery import shared_task
from datetime import datetime, timezone, UTC
from app.worker.celery_app import celery
from sqlalchemy import update, or_

from app.db.session import SyncSessionLocal as SessionLocal
from app.models.notification import Notification, NotificationStatus, NotificationChannel
from app.channels.email import send_email
from app.models.appointment import Appointment  # noqa: F401
from app.models.user import User             # noqa: F401
from app.models.professional import Professional             # noqa: F401



CHANNEL_HANDLERS = {
    NotificationChannel.email: send_email,
    # NotificationChannel.sms: send_sms,
    # NotificationChannel.whatsapp: send_whatsapp,
}


@celery.task(name="app.worker.tasks.dispatch_pending_notifications")
def dispatch_pending_notifications():
    db = SessionLocal()
    now = datetime.now(timezone.utc)
    print(now)
    print("Aaaaaaaaaaaaaaaaaaaaaaaaaaaaa")
    try:
        result = db.execute(
            update(Notification)
            .where(
                Notification.status.in_([
                    NotificationStatus.pending,
                    NotificationStatus.scheduled,
                ]),
                or_(
                    Notification.scheduled_at.is_(None),   # ← envio imediato
                    Notification.scheduled_at <= now,
                ),
                Notification.attempts < Notification.max_attempts,
            )
            .values(status=NotificationStatus.processing)  # ← nome mais claro
            .returning(Notification.id)
            .execution_options(synchronize_session=False)
        )
        ids = result.scalars().all()
        db.commit()

        for notification_id in ids:
            process_notification.delay(str(notification_id))

    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


@celery.task(
    name="app.worker.tasks.process_notification",
    bind=True,
    max_retries=3,
)
def process_notification(self, notification_id: str):
    db = SessionLocal()
    try:
        notification = db.get(Notification, notification_id)

        if not notification:
            return

        if notification.scheduled_at > datetime.now(UTC):
            return  # ainda não é hora

        # Protecção: evita reprocessar se já foi enviado por outro worker
        if notification.status == NotificationStatus.sent:
            return

        handler = CHANNEL_HANDLERS.get(notification.channel)
        if not handler:
            raise ValueError(f"Canal sem handler: {notification.channel}")

        handler(
            recipient=notification.recipient_contact,
            subject=notification.title,
            body=notification.message,
        )
        print(notification.recipient_contact)

        # Sucesso — incrementa e marca como enviado
        notification.attempts += 1
        notification.status = NotificationStatus.sent
        notification.sent_at = datetime.now(timezone.utc)
        notification.error_message = None
        db.commit()

    except Exception as exc:
        db.rollback()

        # Recarrega após rollback para não trabalhar com estado sujo
        notification = db.get(Notification, notification_id)
        if notification:
            notification.attempts += 1
            notification.error_message = str(exc)
            exhausted = notification.attempts >= notification.max_attempts

            notification.status = (
                NotificationStatus.failed
                if exhausted
                else NotificationStatus.scheduled  # Beat vai reapanhá-la
            )
            db.commit()

            if not exhausted:
                raise self.retry(
                    exc=exc,
                    countdown=60 * (2 ** self.request.retries),  # 60s, 120s, 240s
                )
    finally:
        db.close()
