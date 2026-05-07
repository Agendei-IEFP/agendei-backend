from decimal import Decimal

from sqlalchemy import Boolean, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.mixins import Base, TimestampMixin, ULIDMixin
from app.models.professional_store import ProfessionalStore


class Offering(Base, ULIDMixin, TimestampMixin):
    __tablename__ = "offerings"

    professional_store_id: Mapped[str] = mapped_column(
        String(26), ForeignKey("professional_stores.id")
    )
    name: Mapped[str] = mapped_column(String(100))
    description: Mapped[str | None] = mapped_column(Text)
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    duration_minutes: Mapped[int] = mapped_column(Integer)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    professional_store: Mapped[ProfessionalStore] = relationship("ProfessionalStore")
