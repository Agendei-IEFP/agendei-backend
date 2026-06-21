from datetime import time

from sqlalchemy import Boolean, ForeignKey, Integer, String, Time, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.mixins import Base, ULIDMixin
from app.models.professional import Professional


class WorkSchedule(Base, ULIDMixin):
    __tablename__ = "work_schedules"
    __table_args__ = (UniqueConstraint("professional_id", "weekday"),)

    professional_id: Mapped[str] = mapped_column(
        String(26), ForeignKey("professionals.id")
    )
    weekday: Mapped[int] = mapped_column(Integer)  # 0=Monday ... 6=Sunday
    start_time: Mapped[time] = mapped_column(Time)
    end_time: Mapped[time] = mapped_column(Time)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    professional: Mapped[Professional] = relationship("Professional")
