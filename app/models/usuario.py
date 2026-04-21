import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.mixins import Base, TimestampMixin, ULIDMixin


class RoleEnum(str, enum.Enum):
    cliente = "cliente"
    profissional = "profissional"
    admin_loja = "admin_loja"


class Usuario(Base, ULIDMixin, TimestampMixin):
    __tablename__ = "usuarios"

    nome: Mapped[str] = mapped_column(String(100))
    email: Mapped[str] = mapped_column(String(255), unique=True)
    senha_hash: Mapped[str] = mapped_column(String(255))
    telefone: Mapped[str | None] = mapped_column(String(20))
    role: Mapped[RoleEnum] = mapped_column(Enum(RoleEnum), nullable=False)
    accepted_terms_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    accepted_terms_version: Mapped[str | None] = mapped_column(String(10))
    anonymized_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
