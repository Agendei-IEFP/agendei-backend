from datetime import datetime
from pydantic import BaseModel, ConfigDict
from app.schemas.store import StorePublic

base_config = ConfigDict(from_attributes=True)

class ProfessionalBase(BaseModel):
    bio: str | None = None
    photo_url: str | None = None

class ProfessionalSelfCreate(ProfessionalBase):
    pass

class ProfessionalUpdate(ProfessionalBase):
    is_active: bool | None = None

class ProfessionalPublic(ProfessionalBase):
    model_config = base_config
    id: str
    user_id: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

class ProfessionalWithNamePublic(ProfessionalPublic):
    name: str
    professional_store_id: str

class ProfessionalStorePublic(BaseModel):
    model_config = base_config
    id: str
    professional_id: str
    store_id: str
    is_active: bool
    store: StorePublic
    created_at: datetime
    updated_at: datetime