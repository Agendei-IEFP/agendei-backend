from pydantic import BaseModel, ConfigDict, field_validator, model_validator
from typing import Optional
from datetime import time


class HorarioTrabalhoCreate(BaseModel):
    """
    dia_semana: 0=Segunda, 1=Terça, ..., 6=Domingo
    Segue o padrão do Python: date.weekday()
    """
    dia_semana: int
    hora_inicio: time
    hora_fim: time

    @field_validator("dia_semana")
    @classmethod
    def dia_valido(cls, v: int) -> int:
        if v not in range(7):
            raise ValueError("dia_semana deve ser entre 0 (segunda) e 6 (domingo)")
        return v

    @model_validator(mode="after")
    def horario_consistente(self) -> "HorarioTrabalhoCreate":
        if self.hora_fim <= self.hora_inicio:
            raise ValueError("hora_fim deve ser depois de hora_inicio")
        return self


class HorarioTrabalhoUpdate(BaseModel):
    hora_inicio: Optional[time] = None
    hora_fim: Optional[time] = None
    is_active: Optional[bool] = None


class HorarioTrabalhoPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    profissional_id: str
    dia_semana: int
    hora_inicio: time
    hora_fim: time
    is_active: bool