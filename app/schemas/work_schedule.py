from datetime import time

from pydantic import BaseModel, ConfigDict, field_validator, model_validator


class WorkScheduleEntry(BaseModel):
    """Single weekday entry for bulk upsert. weekday: 0=Monday ... 6=Sunday"""

    weekday: int
    start_time: time
    end_time: time
    is_active: bool = True

    @field_validator("weekday")
    @classmethod
    def valid_weekday(cls, v: int) -> int:
        if v not in range(7):
            raise ValueError("weekday deve ser entre 0 (segunda) e 6 (domingo)")
        return v

    @model_validator(mode="after")
    def consistent_schedule(self) -> "WorkScheduleEntry":
        if self.is_active and self.end_time <= self.start_time:
            raise ValueError("end_time deve ser depois de start_time")
        return self


class WorkSchedulePublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    professional_id: str
    weekday: int
    start_time: time
    end_time: time
    is_active: bool


class WorkScheduleBulkUpsert(BaseModel):
    schedules: list[WorkScheduleEntry]
