from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict

from app.models.store import StoreType


class StoreCreate(BaseModel):
    name: str
    description: str | None = None
    phone: str | None = None
    email: str | None = None
    address: str | None = None
    logo_url: str | None = None
    store_type: StoreType | None = None


class StoreUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    phone: str | None = None
    email: str | None = None
    address: str | None = None
    logo_url: str | None = None
    store_type: StoreType | None = None


class StorePublic(BaseModel):
    id: str
    owner_id: str
    name: str
    description: str | None
    phone: str | None
    email: str | None
    address: str | None
    logo_url: str | None
    is_active: bool
    store_type: StoreType | None
    created_at: datetime
    updated_at: datetime
    professional_count: int = 0
    service_count: int = 0

    model_config = ConfigDict(from_attributes=True)


class StoreOfferingPublic(BaseModel):
    service_id: str
    service_name: str
    effective_price: Decimal
    effective_duration_minutes: int
