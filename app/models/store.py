import enum

from sqlalchemy import Boolean, Column, Enum, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.mixins import Base, TimestampMixin, ULIDMixin
from app.models.user import User


class StoreType(str, enum.Enum):
    hair_salon = "hair_salon"
    barbershop = "barbershop"
    nails = "nails"
    aesthetics = "aesthetics"
    massage = "massage"
    treatments = "treatments"


class Store(Base, ULIDMixin, TimestampMixin):
    __tablename__ = "stores"

    owner_id: Mapped[str] = mapped_column(String(26), ForeignKey("users.id"))
    name: Mapped[str] = mapped_column(String(100))
    description: Mapped[str | None] = mapped_column(Text)
    phone: Mapped[str | None] = mapped_column(String(20))
    email: Mapped[str | None] = mapped_column(String(255))
    address: Mapped[str | None] = mapped_column(String(255))
    logo_url: Mapped[str | None] = mapped_column(String(500))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    store_types = Column(
        ARRAY(Enum(StoreType, name="storetype")),
        nullable=False,
        default=list,
        server_default="{}",
    )

    owner: Mapped[User] = relationship("User")
