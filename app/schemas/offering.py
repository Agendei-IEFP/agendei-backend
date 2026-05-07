from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, field_validator


class OfferingCreate(BaseModel):
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


class OfferingUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    price: Decimal | None = None
    duration_minutes: int | None = None
    is_active: bool | None = None


class OfferingPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    professional_store_id: str
    name: str
    description: str | None
    price: Decimal
    duration_minutes: int
    is_active: bool
    created_at: datetime
    updated_at: datetime
