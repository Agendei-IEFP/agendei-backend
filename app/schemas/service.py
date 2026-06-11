from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, ConfigDict, field_validator
from app.schemas.validators import validate_duration, validate_price

class ServiceBase(BaseModel):
    name: str | None = None
    description: str | None = None
    default_price: Decimal | None = None
    default_duration_minutes: int | None = None

class ServiceCreate(ServiceBase):
    name: str  
    default_price: Decimal
    default_duration_minutes: int

    @field_validator("default_duration_minutes")
    @classmethod
    def min_dur(cls, v: int) -> int: return validate_duration(v)  # type: ignore

    @field_validator("default_price")
    @classmethod
    def pos_prc(cls, v: Decimal) -> Decimal: return validate_price(v)  # type: ignore

class ServiceUpdate(ServiceBase):
    is_active: bool | None = None

    @field_validator("default_duration_minutes")
    @classmethod
    def min_dur(cls, v: int | None) -> int | None: return validate_duration(v)

    @field_validator("default_price")
    @classmethod
    def pos_prc(cls, v: Decimal | None) -> Decimal | None: return validate_price(v)

class ServicePublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    professional_id: str
    name: str
    description: str | None
    default_price: Decimal
    default_duration_minutes: int
    is_active: bool
    created_at: datetime
    updated_at: datetime