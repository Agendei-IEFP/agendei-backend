from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.user import RoleEnum


class UserUpdate(BaseModel):
    name: str | None = None
    phone: str | None = None
    email: str | None = None


class PasswordChange(BaseModel):
    current_password: str
    new_password: str


class UserPublic(BaseModel):
    id: str
    name: str
    email: str
    phone: str | None
    role: RoleEnum
    created_at: datetime
    accepted_terms_at: datetime | None
    accepted_terms_version: str | None

    model_config = ConfigDict(from_attributes=True)
