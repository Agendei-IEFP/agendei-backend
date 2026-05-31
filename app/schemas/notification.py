from datetime import datetime
from pydantic import BaseModel, ConfigDict
from typing import Optional
from app.models.notification import (
    NotificationType,
    RecipientType,
    NotificationChannel,
    NotificationStatus,
    )


# Base
class NotificationBase(BaseModel):
    notification_type: NotificationType
    channel: NotificationChannel
    recipient_contact: str
    recipient_id: str
    recipient_type: RecipientType
    appointment_id: Optional[str] = None
    title: Optional[str] = None
    message: str
    scheduled_at: datetime #Quando a notificação deve ser enviada


# Create
class NotificationCreate(NotificationBase):
    pass


# Update
class NotificationUpdateStatus(BaseModel):
    status: Optional[NotificationStatus] = None
    attempts: Optional[int] = None
    error_message: Optional[str] = None
    sent_at: Optional[datetime] = None


# Public (API response)
class NotificationPublic(NotificationBase):
    id: str
    status: NotificationStatus
    attempts: int
    error_message: Optional[str] = None
    sent_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# List view
class NotificationList(BaseModel):
    id: str
    notification_type: str
    channel: str
    recipient_id: str
    appointment_id: Optional[str] = None
    recipient_type: str
    status: NotificationStatus
    scheduled_at: datetime
    sent_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
