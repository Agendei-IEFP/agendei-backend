from datetime import datetime
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, ConfigDict, computed_field, field_validator
from app.schemas.service import ServicePublic
from app.schemas.validators import validate_duration, validate_price

class OfferingBase(BaseModel):
    price_override: Optional[Decimal] = None
    duration_override: Optional[int] = None

    @field_validator("duration_override")
    @classmethod
    def min_dur(cls, v: int | None) -> int | None: return validate_duration(v)

    @field_validator("price_override")
    @classmethod
    def pos_prc(cls, v: Decimal | None) -> Decimal | None: return validate_price(v)

class OfferingCreate(OfferingBase):
    service_id: str

class OfferingUpdate(OfferingBase):
    is_enabled: bool | None = None

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