from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession


from app.db.session import get_db
from app.schemas.notification import (
    NotificationCreate,
    NotificationPublic, NotificationUpdateStatus,

)
from app.services import notification_service
from app.models.user import User
from app.core.dependencies import get_current_user
from app.models.notification import NotificationStatus, RecipientType, Notification
from app.limiter.limiter import limiter
from sqlalchemy.orm import Session
#from app.worker.tasks import process_notification


router = APIRouter(prefix="/notifications", tags=["notifications"])

# @router.post("/notifications", status_code=202)
# async def create_notification(
#     payload: NotificationCreate,
#     db: Session = Depends(get_db),
# ):
#     notif = Notification(**payload.model_dump())
#     db.add(notif)
#     await db.commit()
#     await db.refresh(notif)
#
#     process_notification.delay(str(notif.id))
#     # Envio imediato — sem scheduled_at
#     if notif.scheduled_at is None:
#         process_notification.delay(str(notif.id))
#
#     # Com scheduled_at — o Beat trata disso; não enfileira agora
#     return {"id": str(notif.id), "status": notif.status}

# @router.post(
#     "",
#     response_model=NotificationPublic,
#     status_code=201,
# )
# async def create_notification(
#     data: NotificationCreate,
#     db: AsyncSession = Depends(get_db),
#     user: User = Depends(get_current_user),
# ):
#     return await notification_service.create_notification(db, data)
#

@router.get(
    "/{notification_id}",
    response_model=NotificationPublic,
)
@limiter.limit("5/minute")
async def get_notification(
    request: Request,
    notification_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    notification = await notification_service.get_notification(db, notification_id)

    return notification


@router.get(
    "",
    response_model=list[NotificationPublic],
)
async def list_notifications(
    status: NotificationStatus | None = Query(None),
    recipient_id: str | None = Query(None),
    recipient_type: RecipientType | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return await notification_service.list_notifications(
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
    user: User = Depends(get_current_user),
):
    updated = await notification_service.update_status(db, notification_id, data)

    return updated

