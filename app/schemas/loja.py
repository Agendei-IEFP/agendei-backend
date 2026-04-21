from pydantic import BaseModel, ConfigDict
from typing import Optional


class LojaCreate(BaseModel):
    """Dados necessários para criar uma loja."""
    nome: str
    descricao: Optional[str] = None
    telefone: Optional[str] = None
    endereco: Optional[str] = None
    cidade: Optional[str] = None
    estado: Optional[str] = None


class LojaUpdate(BaseModel):
    """Todos os campos são opcionais — só atualiza o que for enviado."""
    nome: Optional[str] = None
    descricao: Optional[str] = None
    telefone: Optional[str] = None
    endereco: Optional[str] = None
    cidade: Optional[str] = None
    estado: Optional[str] = None
    is_active: Optional[bool] = None


class LojaPublic(BaseModel):
    """O que o frontend recebe. Nunca expõe campos internos."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    nome: str
    descricao: Optional[str]
    telefone: Optional[str]
    endereco: Optional[str]
    cidade: Optional[str]
    estado: Optional[str]
    is_active: bool
    owner_id: str