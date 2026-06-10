from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.schemas.store import StorePublic


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
