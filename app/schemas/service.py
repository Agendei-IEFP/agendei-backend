from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, field_validator


def _validate_duration(v: int | None) -> int | None:
    if v is not None and v < 15:
        raise ValueError("A duração mínima é de 15 minutos")
    return v


def _validate_price(v: Decimal | None) -> Decimal | None:
    if v is not None and v < 0:
        raise ValueError("O preço não pode ser negativo")
    return v


class ServiceCreate(BaseModel):
    name: str
    description: str | None = None
    price: Decimal
    duration_minutes: int

    @field_validator("duration_minutes")
    @classmethod
    def minimum_duration(cls, v: int) -> int:
        if v < 15:
            raise ValueError("A duração mínima é de 15 minutos")
        return v

    @field_validator("price")
    @classmethod
    def positive_price(cls, v: Decimal) -> Decimal:
        if v < 0:
            raise ValueError("O preço não pode ser negativo")
        return v


class ServiceUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    price: Decimal | None = None
    duration_minutes: int | None = None
    is_active: bool | None = None

    @field_validator("duration_minutes")
    @classmethod
    def minimum_duration(cls, v: int | None) -> int | None:
        return _validate_duration(v)

    @field_validator("price")
    @classmethod
    def positive_price(cls, v: Decimal | None) -> Decimal | None:
        return _validate_price(v)


class ServicePublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    professional_id: str
    name: str
    description: str | None
    price: Decimal
    duration_minutes: int
    is_active: bool
    created_at: datetime
    updated_at: datetime
