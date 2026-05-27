from celery import shared_task
from datetime import datetime, timezone
from sqlalchemy import update

from app.db.session import SessionLocal
from app.models.notification import Notification, NotificationStatus, NotificationChannel
from app.channels.email import send_email


CHANNEL_HANDLERS = {
    NotificationChannel.email: send_email,
    # NotificationChannel.sms: send_sms,
    # NotificationChannel.whatsapp: send_whatsapp,
}


@shared_task(name="app.worker.tasks.dispatch_pending_notifications")
def dispatch_pending_notifications():
    db = SessionLocal()
    now = datetime.now(timezone.utc)
    try:
        result = db.execute(
            update(Notification)
            .where(
                Notification.status.in_([
                    NotificationStatus.pending,
                    NotificationStatus.scheduled,
                ]),
                Notification.scheduled_at <= now,
                Notification.attempts < Notification.max_attempts,
            )
            .values(status=NotificationStatus.retrying)
            .returning(Notification.id)
        )
        ids = result.scalars().all()
        db.commit()

        for notification_id in ids:
            process_notification.delay(str(notification_id))

    finally:
        db.close()


@shared_task(
    name="app.worker.tasks.process_notification",
    bind=True,
    max_retries=3,
)
def process_notification(self, notification_id: str):
    db = SessionLocal()
    notification = None
    try:
        notification = db.get(Notification, notification_id)

        if not notification:
            return

        handler = CHANNEL_HANDLERS.get(notification.channel)
        if not handler:
            raise ValueError(f"Canal sem handler: {notification.channel}")

        handler(
            recipient=notification.recipient_contact,
            subject=notification.title,
            body=notification.message,
        )

        notification.attempts += 1
        notification.status = NotificationStatus.sent
        notification.sent_at = datetime.now(timezone.utc)

    except Exception as exc:
        if notification:
            notification.attempts += 1
            notification.error_message = str(exc)
            notification.status = (
                NotificationStatus.failed
                if notification.attempts >= notification.max_attempts
                else NotificationStatus.scheduled
            )
        if notification and notification.status == NotificationStatus.scheduled:
            raise self.retry(
                exc=exc,
                countdown=60 * (2 ** self.request.retries),  # backoff: 60s, 120s, 240s
            )
    finally:
        db.commit()
        db.close()