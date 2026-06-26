from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, model_validator

from app.models.appointment import StatusEnum


class AppointmentCreate(BaseModel):
    professional_id: str
    service_id: str
    starts_at: datetime


class AppointmentUpdate(BaseModel):
    status: StatusEnum
    reason: str | None = None


class AppointmentPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    client_id: str
    professional_id: str
    service_id: str
    store_id: str
    starts_at: datetime
    ends_at: datetime
    status: StatusEnum
    cancelled_by: str | None
    cancellation_reason: str | None
    reminder_sent: bool


class AppointmentClientPublic(BaseModel):
    id: str
    starts_at: datetime
    ends_at: datetime
    status: StatusEnum
    notes: str | None
    cancelled_by: str | None
    cancellation_reason: str | None
    service_name: str | None
    professional_name: str | None
    store_name: str | None
    price: Decimal | None
    duration_minutes: int | None


class AppointmentProfessionalPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    client_id: str
    professional_id: str
    service_id: str
    store_id: str
    starts_at: datetime
    ends_at: datetime
    status: StatusEnum
    cancelled_by: str | None
    cancellation_reason: str | None
    reminder_sent: bool
    client_name: str | None = None
    client_phone: str | None = None
    client_email: str | None = None
    service_name: str | None = None
    duration_minutes: int | None = None
    store_name: str | None = None

    @model_validator(mode="before")
    @classmethod
    def extract_nested(cls, data):
        if isinstance(data, dict):
            return data
        return {
            "id": data.id,
            "client_id": data.client_id,
            "professional_id": data.professional_id,
            "service_id": data.service_id,
            "store_id": data.store_id,
            "starts_at": data.starts_at,
            "ends_at": data.ends_at,
            "status": data.status,
            "cancelled_by": data.cancelled_by,
            "cancellation_reason": data.cancellation_reason,
            "reminder_sent": data.reminder_sent,
            "client_name": data.client.name if data.client else None,
            "client_phone": data.client.phone if data.client else None,
            "client_email": data.client.email if data.client else None,
            "service_name": data.service.name if data.service else None,
            "duration_minutes": data.service.duration_minutes if data.service else None,
            "store_name": data.store.name if data.store else None,
        }


class AppointmentAdminPublic(BaseModel):
    id: str
    starts_at: datetime
    ends_at: datetime
    status: StatusEnum
    client_name: str | None
    professional_name: str | None
    service_name: str | None
    store_name: str | None
    duration_minutes: int | None
    price: Decimal | None


class AvailableSlot(BaseModel):
    start: datetime
    end: datetime
