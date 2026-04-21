from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime
from app.models.agendamento import StatusEnum


class AgendamentoCreate(BaseModel):
    """
    O cliente escolhe o profissional, o serviço e o horário de início.
    data_hora_fim é calculado pelo backend (início + duração do serviço).
    """
    profissional_id: str
    servico_id: str
    data_hora_inicio: datetime


class AgendamentoUpdate(BaseModel):
    """Apenas o status pode ser alterado após criação."""
    status: StatusEnum


class AgendamentoPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    cliente_id: str
    profissional_id: str
    servico_id: str
    data_hora_inicio: datetime
    data_hora_fim: datetime
    status: StatusEnum
    cancelado_por: Optional[str]
    lembrete_enviado: bool


class SlotDisponivel(BaseModel):
    """Um horário disponível retornado pelo algoritmo de slots."""
    inicio: datetime
    fim: datetime