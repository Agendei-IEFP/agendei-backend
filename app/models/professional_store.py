from sqlalchemy import Boolean, ForeignKey, Index, String, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.mixins import Base, TimestampMixin, ULIDMixin
from app.models.professional import Professional
from app.models.store import Store


class ProfessionalStore(Base, ULIDMixin, TimestampMixin):
    __tablename__ = "professional_stores"

    professional_id: Mapped[str] = mapped_column(
        String(26), ForeignKey("professionals.id")
    )
    store_id: Mapped[str] = mapped_column(String(26), ForeignKey("stores.id"))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    professional: Mapped[Professional] = relationship("Professional")
    store: Mapped[Store] = relationship("Store")

    __table_args__ = (
        Index(
            "ix_professional_stores_pair_unique",
            "professional_id",
            "store_id",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
    )
