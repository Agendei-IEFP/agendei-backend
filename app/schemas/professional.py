from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, field_validator

from app.schemas.store import StorePublic


class ProfessionalCreate(BaseModel):
    name: str
    email: EmailStr
    password: str
    phone: str | None = None

    @field_validator("password")
    @classmethod
    def password_min_length(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("A senha deve ter no mínimo 8 caracteres")
        return v


class ProfessionalSelfCreate(BaseModel):
    bio: str | None = None
    photo_url: str | None = None


class ProfessionalUpdate(BaseModel):
    bio: str | None = None
    photo_url: str | None = None
    is_active: bool | None = None


class ProfessionalPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    store_id: str
    bio: str | None
    photo_url: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class ProfessionalWithNamePublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    store_id: str
    name: str
    bio: str | None
    photo_url: str | None
    is_active: bool


class ProfessionalWithStorePublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    store_id: str
    name: str
    bio: str | None
    photo_url: str | None
    is_active: bool
    store_name: str
    store: StorePublic
