from datetime import datetime
from decimal import Decimal
from typing import Annotated, Optional

from pydantic import BaseModel, ConfigDict, computed_field, field_validator

from app.schemas.service import ServicePublic


def _validate_duration(v: int | None) -> int | None:
    if v is not None and v < 15:
        raise ValueError("A duração mínima é de 15 minutos")
    return v


def _validate_price(v: Decimal | None) -> Decimal | None:
    if v is not None and v < 0:
        raise ValueError("O preço não pode ser negativo")
    return v


class OfferingCreate(BaseModel):
    service_id: str
    price_override: Decimal | None = None
    duration_override: int | None = None

    @field_validator("duration_override")
    @classmethod
    def minimum_duration(cls, v: int | None) -> int | None:
        return _validate_duration(v)

    @field_validator("price_override")
    @classmethod
    def positive_price(cls, v: Decimal | None) -> Decimal | None:
        return _validate_price(v)


class OfferingUpdate(BaseModel):
    # Optional[X] instead of X | None so that an explicit null in JSON
    # is preserved through model_dump(exclude_unset=True), allowing the
    # caller to clear an override back to the service default.
    price_override: Optional[Decimal] = None
    duration_override: Optional[int] = None
    is_enabled: bool | None = None

    @field_validator("duration_override")
    @classmethod
    def minimum_duration(cls, v: int | None) -> int | None:
        return _validate_duration(v)

    @field_validator("price_override")
    @classmethod
    def positive_price(cls, v: Decimal | None) -> Decimal | None:
        return _validate_price(v)


class OfferingPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    service_id: str
    professional_store_id: str
    price_override: Decimal | None
    duration_override: int | None
    is_enabled: bool
    service: ServicePublic
    created_at: datetime
    updated_at: datetime

    @computed_field
    @property
    def effective_price(self) -> Decimal:
        return self.price_override if self.price_override is not None else self.service.default_price

    @computed_field
    @property
    def effective_duration_minutes(self) -> int:
        return self.duration_override if self.duration_override is not None else self.service.default_duration_minutes
