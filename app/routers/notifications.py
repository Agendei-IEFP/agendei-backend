from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.notification import (
    NotificationCreate,
    NotificationPublic, NotificationUpdateStatus,
)
from app.services.notification_service import NotificationService


router = APIRouter(prefix="/notifications", tags=["notifications"])

service = NotificationService()


# CREATE
@router.post(
    "",
    response_model=NotificationPublic,
    status_code=201,
)
async def create_notification(
    data: NotificationCreate,
    db: AsyncSession = Depends(get_db),
):
    return await service.create_notification(db, data)


# GET BY ID
@router.get(
    "/{notification_id}",
    response_model=NotificationPublic,
)
async def get_notification(
    notification_id: str,
    db: AsyncSession = Depends(get_db),
):
    notification = await service.get_notification(db, notification_id)

    return notification


# LIST WITH FILTERS
@router.get(
    "",
    response_model=list[NotificationPublic],
)
async def list_notifications(
    status: str | None = Query(None),
    recipient_id: str | None = Query(None),
    recipient_type: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    return await service.list_notifications(
        db,
        status=status,
        recipient_id=recipient_id,
        recipient_type=recipient_type,
        limit=limit,
        offset=offset,
    )


@router.patch(
    "/{notification_id}/status",
    response_model=NotificationPublic,
)
async def update_notification_status(
    notification_id: str,
    data: NotificationUpdateStatus,
    db: AsyncSession = Depends(get_db),
):
    updated = await service.update_status(db, notification_id, data)

    if not updated:
        raise HTTPException(status_code=404, detail="Notification not found")

    return updated

