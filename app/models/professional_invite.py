from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.mixins import Base, TimestampMixin, ULIDMixin
from app.models.store import Store
from app.models.user import User


class ProfessionalInvite(Base, ULIDMixin, TimestampMixin):
    __tablename__ = "professional_invites"

    token: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    store_id: Mapped[str] = mapped_column(String(26), ForeignKey("stores.id"))
    created_by: Mapped[str] = mapped_column(String(26), ForeignKey("users.id"))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    accepted_user_id: Mapped[str | None] = mapped_column(
        String(26), ForeignKey("users.id")
    )

    store: Mapped[Store] = relationship("Store")
    creator: Mapped[User] = relationship("User", foreign_keys=[created_by])
    accepted_user: Mapped[User | None] = relationship(
        "User", foreign_keys=[accepted_user_id]
    )
