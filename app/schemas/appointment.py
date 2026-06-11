from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, ConfigDict
from app.models.appointment import StatusEnum

base_config = ConfigDict(from_attributes=True)

class AppointmentCreate(BaseModel):
    professional_store_id: str
    offering_id: str
    starts_at: datetime

class AppointmentUpdate(BaseModel):
    status: StatusEnum
    reason: str | None = None

class AppointmentPublic(BaseModel):
    model_config = base_config
    id: str
    starts_at: datetime
    ends_at: datetime
    status: StatusEnum
    cancelled_by: str | None
    cancellation_reason: str | None


class AppointmentProfessionalPublic(AppointmentPublic):
    client_id: str
    professional_id: str
    professional_store_id: str
    offering_id: str
    reminder_sent: bool
    client_name: str | None = None
    client_phone: str | None = None
    client_email: str | None = None
    service_name: str | None = None
    duration_minutes: int | None = None
    store_name: str | None = None

class AppointmentClientPublic(AppointmentPublic):
    notes: str | None
    service_name: str | None
    professional_name: str | None
    store_name: str | None
    effective_price: Decimal | None
    effective_duration_minutes: int | None

class AvailableSlot(BaseModel):
    start: datetime
    end: datetime