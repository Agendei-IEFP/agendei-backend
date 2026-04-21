from pydantic import BaseModel, ConfigDict, field_validator
from typing import Optional
from decimal import Decimal


class ServicoCreate(BaseModel):
    nome: str
    descricao: Optional[str] = None
    preco: Decimal
    duracao_minutos: int

    @field_validator("duracao_minutos")
    @classmethod
    def duracao_positiva(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("A duração deve ser maior que zero")
        return v

    @field_validator("preco")
    @classmethod
    def preco_positivo(cls, v: Decimal) -> Decimal:
        if v < 0:
            raise ValueError("O preço não pode ser negativo")
        return v


class ServicoUpdate(BaseModel):
    nome: str | None = None
    descricao: str | None = None
    preco: Decimal | None = None
    duracao_minutos: int | None = None
    is_active: bool | None = None


class ServicoPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    profissional_id: str
    nome: str
    descricao: str | None
    preco: Decimal
    duracao_minutos: int
    is_active: bool