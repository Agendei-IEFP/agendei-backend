from pydantic import BaseModel, ConfigDict
from typing import Optional


class ProfissionalCreate(BaseModel):
    """
    Para criar um profissional, o admin_loja escolhe qual usuário
    (com role=profissional) vai trabalhar na sua loja.
    """
    usuario_id: str
    bio: Optional[str] = None
    foto_url: Optional[str] = None


class ProfissionalUpdate(BaseModel):
    bio: Optional[str] = None
    foto_url: Optional[str] = None
    is_active: Optional[bool] = None


class ProfissionalPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    usuario_id: str
    loja_id: str
    bio: Optional[str]
    foto_url: Optional[str]
    is_active: bool