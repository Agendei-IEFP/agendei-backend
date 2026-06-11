from datetime import time
from pydantic import BaseModel, ConfigDict
from app.schemas.base_schedule import WeekdayScheduleBase

class StoreAvailabilityCreate(WeekdayScheduleBase):
    """Herda automaticamente a validação de weekday e horários coerentes"""
    pass

class StoreAvailabilityUpdate(BaseModel):
    start_time: time | None = None
    end_time: time | None = None
    is_active: bool | None = None

class StoreAvailabilityPublic(WeekdayScheduleBase):
    model_config = ConfigDict(from_attributes=True)
    id: str
    professional_store_id: str
    is_active: bool

class StoreAvailabilityBulkReplace(BaseModel):
    blocks: list[StoreAvailabilityCreate]