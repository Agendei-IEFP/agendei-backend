from typing import Sequence
from datetime import datetime, UTC
from fastapi import HTTPException
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification import Notification
from app.schemas.notification import (
    NotificationCreate,
    NotificationPublic,
    NotificationUpdateStatus,
)
from app.services.auth_service import user_validity


# CREATE
async def create_notification(
        db: AsyncSession,
        data: NotificationCreate,
) -> NotificationPublic:
    notification = Notification(**data.model_dump())
    db.add(notification)
    await db.commit()
    await db.refresh(notification)
    return NotificationPublic.model_validate(notification)


# GET BY ID
async def get_notification(
        db: AsyncSession,
        notification_id: str,
) -> NotificationPublic | None:
    result = await db.execute(
        select(Notification).where(Notification.id == notification_id)
    )
    notification = result.scalar_one_or_none()

    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")

    return NotificationPublic.model_validate(notification)


# LIST
async def list_notifications(
        db: AsyncSession,
        *,
        status: str | None = None,
        recipient_id: str | None = None,
        recipient_type: str | None = None,
        limit: int = 50,
        offset: int = 0,
) -> Sequence[NotificationPublic]:
    query = select(Notification)

    if status:
        query = query.where(Notification.status == status)

    if recipient_id:
        user = await user_validity(db, recipient_id)
        query = query.where(Notification.recipient_id == user.id)

    if recipient_type:
        query = query.where(Notification.recipient_type == recipient_type)

    query = query.limit(limit).offset(offset)

    result = await db.execute(query)
    notifications = result.scalars().all()

    return [
        NotificationPublic.model_validate(n)
        for n in notifications
    ]


# UPDATE STATUS (worker)
async def update_status(
        db: AsyncSession,
        notification_id: str,
        data: NotificationUpdateStatus,
) -> NotificationPublic:
    # Buscar a notificação
    notification = await get_notification(db, notification_id)

    # Atualizar campos permitidos
    notification.status = data.status
    notification.attempts = data.attempts
    notification.error_message = data.error_message
    notification.sent_at = data.sent_at

    # Salvar
    await db.commit()
    await db.refresh(notification)

    return NotificationPublic.model_validate(notification)


async def get_pending_notifications(
        db: AsyncSession,
        limit: int = 50,
):
    query = (
        select(Notification)
        .where(Notification.status == "pending")
        .where(Notification.scheduled_at <= datetime.now(UTC))
        .limit(limit)
    )

    result = await db.execute(query)
    return result.scalars().all()
