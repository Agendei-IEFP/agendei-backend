from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr


class ProfissionalCreate(BaseModel):
    nome: str
    email: EmailStr
    senha: str
    bio: str | None = None
    foto_url: str | None = None


class ProfissionalUpdate(BaseModel):
    bio: str | None = None
    foto_url: str | None = None
    is_active: bool | None = None


class ProfissionalPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    usuario_id: str
    loja_id: str
    bio: str | None
    foto_url: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime
