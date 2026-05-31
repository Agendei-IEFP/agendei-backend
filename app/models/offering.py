from decimal import Decimal

from sqlalchemy import Boolean, ForeignKey, Index, Integer, Numeric, String, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.mixins import Base, TimestampMixin, ULIDMixin
from app.models.professional_store import ProfessionalStore
from app.models.service import Service


class Offering(Base, ULIDMixin, TimestampMixin):
    __tablename__ = "offerings"

    service_id: Mapped[str] = mapped_column(String(26), ForeignKey("services.id"))
    professional_store_id: Mapped[str] = mapped_column(
        String(26), ForeignKey("professional_stores.id")
    )
    price_override: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    duration_override: Mapped[int | None] = mapped_column(Integer)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True)

    service: Mapped[Service] = relationship("Service")
    professional_store: Mapped[ProfessionalStore] = relationship("ProfessionalStore")

    __table_args__ = (
        Index(
            "ix_offerings_service_link_unique",
            "service_id",
            "professional_store_id",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
    )
