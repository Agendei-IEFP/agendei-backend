from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, field_validator


class ServicoCreate(BaseModel):
    nome: str
    descricao: str | None = None
    preco: Decimal
    duracao_minutos: int

    @field_validator("duracao_minutos")
    @classmethod
    def duracao_minima(cls, v: int) -> int:
        if v < 15:
            raise ValueError("A duração mínima é de 15 minutos")
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
    created_at: datetime
    updated_at: datetime
