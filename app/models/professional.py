from sqlalchemy import Boolean, ForeignKey, Index, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.mixins import Base, TimestampMixin, ULIDMixin
from app.models.store import Store
from app.models.user import User


class Professional(Base, ULIDMixin, TimestampMixin):
    __tablename__ = "professionals"

    user_id: Mapped[str] = mapped_column(String(26), ForeignKey("users.id"))
    store_id: Mapped[str] = mapped_column(String(26), ForeignKey("stores.id"))
    bio: Mapped[str | None] = mapped_column(Text)
    photo_url: Mapped[str | None] = mapped_column(String(500))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    user: Mapped[User] = relationship("User")
    store: Mapped[Store] = relationship("Store")

    __table_args__ = (
        Index(
            "ix_professionals_user_id_unique",
            "user_id",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
    )
