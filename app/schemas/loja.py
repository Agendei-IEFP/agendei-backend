from datetime import datetime

from pydantic import BaseModel, ConfigDict


class LojaCreate(BaseModel):
    nome: str
    descricao: str | None = None
    telefone: str | None = None
    email: str | None = None
    endereco: str | None = None
    logo_url: str | None = None


class LojaUpdate(BaseModel):
    nome: str | None = None
    descricao: str | None = None
    telefone: str | None = None
    email: str | None = None
    endereco: str | None = None
    logo_url: str | None = None


class LojaPublic(BaseModel):
    id: str
    owner_id: str
    nome: str
    descricao: str | None
    telefone: str | None
    email: str | None
    endereco: str | None
    logo_url: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
