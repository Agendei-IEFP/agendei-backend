from datetime import datetime
from pydantic import BaseModel, Field
from typing import Optional, Literal, Any
from pydantic import ConfigDict
from enum import Enum


class NotificationType(str, Enum):
    reminder = "reminder"
    confirmation = "confirmation"
    cancellation = "cancellation"
    evaluation = "evaluation"


class RecipientType(str, Enum):
    customer = "customer"
    professional = "professional"


class NotificationChannel(str, Enum):
    email = "email"
    sms = "sms"
    whatsapp = "whatsapp"


# -----------------------------
# Base
# -----------------------------
class NotificationBase(BaseModel):
    type: NotificationType
    channel: NotificationChannel
    recipient_id: int
    recipient_type: RecipientType
    appointment_id: Optional[int] = None
    title: Optional[str] = None
    message: str
    payload: Optional[dict[str, Any]] = None #JSON para guardar outros dados da notificação
    scheduled_at: datetime #Quando a notificação deve ser enviada


# -----------------------------
# Create
# -----------------------------
class NotificationCreate(NotificationBase):
    pass


# -----------------------------
# Update
# -----------------------------
class NotificationUpdateStatus(BaseModel):
    status: Optional[str] = None
    attempts: Optional[int] = None
    error_message: Optional[str] = None
    sent_at: Optional[datetime] = None


# -----------------------------
# Public (API response)
# -----------------------------
class NotificationPublic(NotificationBase):
    id: int
    status: str
    attempts: int
    error_message: Optional[str] = None
    sent_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# -----------------------------
# List view
# -----------------------------
class NotificationList(BaseModel):
    id: int
    type: str
    channel: str
    recipient_id: int
    recipient_type: str
    status: str
    scheduled_at: datetime
    sent_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
