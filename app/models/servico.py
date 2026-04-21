from decimal import Decimal

from sqlalchemy import Boolean, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.mixins import Base, TimestampMixin, ULIDMixin
from app.models.profissional import Profissional


class Servico(Base, ULIDMixin, TimestampMixin):
    __tablename__ = "servicos"

    profissional_id: Mapped[str] = mapped_column(String(26), ForeignKey("profissionais.id"))
    nome: Mapped[str] = mapped_column(String(100))
    descricao: Mapped[str | None] = mapped_column(Text)
    preco: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    duracao_minutos: Mapped[int] = mapped_column(Integer)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    profissional: Mapped[Profissional] = relationship("Profissional")
