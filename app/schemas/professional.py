from datetime import datetime

from pydantic import BaseModel, ConfigDict


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
    bio: str | None
    photo_url: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class ProfessionalStorePublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    professional_id: str
    store_id: str
    is_active: bool
    created_at: datetime
    updated_at: datetime


class ProfessionalWithStorePublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    name: str
    bio: str | None
    photo_url: str | None
    is_active: bool
    store_id: str
    store_name: str
