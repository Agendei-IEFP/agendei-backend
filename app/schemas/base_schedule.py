from datetime import time
from pydantic import BaseModel, field_validator, model_validator

class WeekdayScheduleBase(BaseModel):
    """
    Classe base abstrata para horários semanais.
    weekday: 0=Segunda-feira, 1=Terça-feira, ..., 6=Domingo
    Convenção do Python: date.weekday()
    """
    weekday: int
    start_time: time
    end_time: time

    @field_validator("weekday")
    @classmethod
    def valid_weekday(cls, v: int) -> int:
        if v not in range(7):
            raise ValueError("weekday deve ser entre 0 (segunda) e 6 (domingo)")
        return v

    @model_validator(mode="after")
    def consistent_schedule(self) -> "WeekdayScheduleBase":
        if self.end_time <= self.start_time:
            raise ValueError("end_time deve ser depois de start_time")
        return self