import enum
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.mixins import Base, TimestampMixin, ULIDMixin
from app.models.user import User
from app.models.professional import Professional
from app.models.service import Service
from app.models.store import Store


class StatusEnum(str, enum.Enum):
    confirmed = "confirmed"
    cancelled = "cancelled"
    completed = "completed"


class Appointment(Base, ULIDMixin, TimestampMixin):
    __tablename__ = "appointments"

    client_id: Mapped[str] = mapped_column(String(26), ForeignKey("users.id"))
    professional_id: Mapped[str] = mapped_column(String(26), ForeignKey("professionals.id"))
    service_id: Mapped[str] = mapped_column(String(26), ForeignKey("services.id"))
    store_id: Mapped[str] = mapped_column(String(26), ForeignKey("stores.id"))
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    status: Mapped[StatusEnum] = mapped_column(Enum(StatusEnum), default=StatusEnum.confirmed)
    notes: Mapped[str | None] = mapped_column(Text)
    cancelled_by: Mapped[str | None] = mapped_column(String(26))
    cancellation_reason: Mapped[str | None] = mapped_column(Text)
    reminder_sent: Mapped[bool] = mapped_column(Boolean, default=False)

    client: Mapped[User] = relationship("User", foreign_keys=[client_id])
    professional: Mapped[Professional] = relationship("Professional")
    service: Mapped[Service] = relationship("Service")
    store: Mapped[Store] = relationship("Store")
