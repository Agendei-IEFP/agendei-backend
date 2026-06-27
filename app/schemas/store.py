from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, field_validator

from app.models.store import StoreType


def _validate_store_types(v: list[StoreType] | None) -> list[StoreType] | None:
    if v is None:
        return v
    if len(v) > 3:
        raise ValueError("Máximo de 3 tipos por estabelecimento")
    if len(v) != len(set(v)):
        raise ValueError("Tipos duplicados não são permitidos")
    return v


class StoreCreate(BaseModel):
    name: str
    description: str | None = None
    phone: str | None = None
    email: str | None = None
    address: str | None = None
    logo_url: str | None = None
    banner_url: str | None = None
    store_types: list[StoreType] = []

    @field_validator("store_types")
    @classmethod
    def validate_store_types(cls, v: list[StoreType]) -> list[StoreType]:
        return _validate_store_types(v)  # type: ignore[return-value]


class StoreUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    phone: str | None = None
    email: str | None = None
    address: str | None = None
    logo_url: str | None = None
    banner_url: str | None = None
    store_types: list[StoreType] | None = None
    is_active: bool | None = None

    @field_validator("store_types")
    @classmethod
    def validate_store_types(cls, v: list[StoreType] | None) -> list[StoreType] | None:
        return _validate_store_types(v)


class StorePublic(BaseModel):
    id: str
    owner_id: str
    name: str
    description: str | None
    phone: str | None
    email: str | None
    address: str | None
    logo_url: str | None
    banner_url: str | None
    is_active: bool
    store_types: list[StoreType]
    created_at: datetime
    updated_at: datetime
    professional_count: int = 0
    service_count: int = 0

    model_config = ConfigDict(from_attributes=True)


class StoreServicePublic(BaseModel):
    service_id: str
    service_name: str
    price: Decimal
    duration_minutes: int
    professional_id: str
    professional_name: str
