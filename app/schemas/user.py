from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.user import RoleEnum


class UserUpdate(BaseModel):
    name: str | None = None
    phone: str | None = None
    email: str | None = None


class UserPublic(BaseModel):
    id: str
    name: str
    email: str
    phone: str | None
    role: RoleEnum
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
