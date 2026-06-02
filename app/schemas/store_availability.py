from datetime import time

from pydantic import BaseModel, ConfigDict, field_validator, model_validator


class StoreAvailabilityCreate(BaseModel):
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
    def consistent_times(self) -> "StoreAvailabilityCreate":
        if self.end_time <= self.start_time:
            raise ValueError("end_time deve ser depois de start_time")
        return self


class StoreAvailabilityUpdate(BaseModel):
    start_time: time | None = None
    end_time: time | None = None
    is_active: bool | None = None


class StoreAvailabilityPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    professional_store_id: str
    weekday: int
    start_time: time
    end_time: time
    is_active: bool


class StoreAvailabilityBulkReplace(BaseModel):
    blocks: list[StoreAvailabilityCreate]
