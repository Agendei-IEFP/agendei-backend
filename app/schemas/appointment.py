from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict

from app.models.appointment import StatusEnum


class AppointmentCreate(BaseModel):
    """
    Client picks the professional-store binding, the offering, and a start time.
    The owning professional is derived from professional_store_id; ends_at is
    computed from the offering duration.
    """
    professional_store_id: str
    offering_id: str
    starts_at: datetime


class AppointmentUpdate(BaseModel):
    status: StatusEnum
    reason: str | None = None


class AppointmentPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    client_id: str
    professional_id: str
    professional_store_id: str
    offering_id: str
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
    effective_price: Decimal | None
    effective_duration_minutes: int | None


class AppointmentProfessionalPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    client_id: str
    professional_id: str
    professional_store_id: str
    offering_id: str
    starts_at: datetime
    ends_at: datetime
    status: StatusEnum
    cancelled_by: str | None
    cancellation_reason: str | None
    reminder_sent: bool
    client_name: str | None = None
    service_name: str | None = None
    duration_minutes: int | None = None
    store_name: str | None = None


class AvailableSlot(BaseModel):
    start: datetime
    end: datetime
