from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, field_validator, model_validator

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

    @model_validator(mode="before")
    @classmethod
    def extract_user_name(cls, data):
        if isinstance(data, dict):
            return data
        return {
            "id": data.id,
            "user_id": data.user_id,
            "store_id": data.store_id,
            "name": data.user.name,
            "bio": data.bio,
            "photo_url": data.photo_url,
            "is_active": data.is_active,
        }


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

    @model_validator(mode="before")
    @classmethod
    def extract_nested(cls, data):
        if isinstance(data, dict):
            return data
        return {
            "id": data.id,
            "user_id": data.user_id,
            "store_id": data.store_id,
            "name": data.user.name,
            "bio": data.bio,
            "photo_url": data.photo_url,
            "is_active": data.is_active,
            "store_name": data.store.name,
            "store": data.store,
        }
