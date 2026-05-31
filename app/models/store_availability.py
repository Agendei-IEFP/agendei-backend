from datetime import time

from sqlalchemy import Boolean, ForeignKey, Integer, String, Time
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.mixins import Base, TimestampMixin, ULIDMixin
from app.models.professional_store import ProfessionalStore


class StoreAvailability(Base, ULIDMixin, TimestampMixin):
    __tablename__ = "store_availabilities"

    professional_store_id: Mapped[str] = mapped_column(
        String(26), ForeignKey("professional_stores.id")
    )
    weekday: Mapped[int] = mapped_column(Integer)  # 0=Monday ... 6=Sunday
    start_time: Mapped[time] = mapped_column(Time)
    end_time: Mapped[time] = mapped_column(Time)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    professional_store: Mapped[ProfessionalStore] = relationship("ProfessionalStore")
