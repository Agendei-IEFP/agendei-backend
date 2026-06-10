from datetime import datetime

from pydantic import BaseModel, EmailStr

from app.schemas.professional import ProfessionalWithStorePublic


class InviteCreatedResponse(BaseModel):
    token: str
    url: str
    expires_at: datetime


class InvitePublic(BaseModel):
    store_id: str
    store_name: str
    expires_at: datetime


class InviteAcceptRequest(BaseModel):
    name: str | None = None
    email: EmailStr | None = None
    password: str | None = None
    phone: str | None = None
    accepted_terms: bool | None = None


class InviteAcceptResponse(BaseModel):
    professional: ProfessionalWithStorePublic
    access_token: str | None = None
    refresh_token: str | None = None
