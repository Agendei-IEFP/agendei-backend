from datetime import datetime, timezone

from sqlalchemy import update, or_
from app.db.session import get_db, AsyncSession
from app.models.notification import Notification, NotificationStatus, NotificationChannel
from app.channels.email import send_email


CHANNEL_HANDLERS = {
    NotificationChannel.email: send_email,
}

async def scan_and_send_reminders():
    async for db in get_db():
        now = datetime.now(timezone.utc)

        result = await db.execute(
            update(Notification)
            .where(
                Notification.status.in_([
                    NotificationStatus.pending,
                    NotificationStatus.scheduled,
                ]),
                or_(
                    Notification.scheduled_at.is_(None),
                    Notification.scheduled_at <= now,
                ),
                Notification.attempts < Notification.max_attempts,
            )
            .values(status=NotificationStatus.processing)
            .returning(Notification.id)
            .execution_options(synchronize_session=False)
        )

        ids = result.scalars().all()
        await db.commit()

        for notification_id in ids:
            await process_notification(db, notification_id)


async def process_notification(db: AsyncSession, notification_id: str):
        notification = await db.get(Notification, notification_id)

        if not notification:
            return

        if notification.scheduled_at and notification.scheduled_at > datetime.now(timezone.utc):
            return

        if notification.status == NotificationStatus.sent:
            return

        handler = CHANNEL_HANDLERS.get(notification.channel)
        if not handler:
            notification.status = NotificationStatus.failed
            notification.error_message = "Canal sem handler"
            await db.commit()
            return

        try:
            handler(
                recipient=notification.recipient_contact,
                subject=notification.title,
                body=notification.message,
            )

            notification.attempts += 1
            notification.status = NotificationStatus.sent
            notification.sent_at = datetime.now(timezone.utc)
            notification.error_message = None

        except Exception as exc:
            notification.attempts += 1
            notification.error_message = str(exc)

            if notification.attempts >= notification.max_attempts:
                notification.status = NotificationStatus.failed
            else:
                notification.status = NotificationStatus.scheduled

        await db.commit()
