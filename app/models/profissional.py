from sqlalchemy import Boolean, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.mixins import Base, TimestampMixin, ULIDMixin
from app.models.usuario import Usuario
from app.models.loja import Loja


class Profissional(Base, ULIDMixin, TimestampMixin):
    __tablename__ = "profissionais"

    usuario_id: Mapped[str] = mapped_column(String(26), ForeignKey("usuarios.id"))
    loja_id: Mapped[str] = mapped_column(String(26), ForeignKey("lojas.id"))
    bio: Mapped[str | None] = mapped_column(Text)
    foto_url: Mapped[str | None] = mapped_column(String(500))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    usuario: Mapped[Usuario] = relationship("Usuario")
    loja: Mapped[Loja] = relationship("Loja")
