import enum
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.mixins import Base, TimestampMixin, ULIDMixin
from app.models.usuario import Usuario
from app.models.profissional import Profissional
from app.models.servico import Servico


class StatusEnum(str, enum.Enum):
    pendente = "pendente"
    confirmado = "confirmado"
    cancelado = "cancelado"
    concluido = "concluido"


class Agendamento(Base, ULIDMixin, TimestampMixin):
    __tablename__ = "agendamentos"

    cliente_id: Mapped[str] = mapped_column(String(26), ForeignKey("usuarios.id"))
    profissional_id: Mapped[str] = mapped_column(String(26), ForeignKey("profissionais.id"))
    servico_id: Mapped[str] = mapped_column(String(26), ForeignKey("servicos.id"))
    data_hora_inicio: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    data_hora_fim: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    status: Mapped[StatusEnum] = mapped_column(Enum(StatusEnum), default=StatusEnum.pendente)
    notas: Mapped[str | None] = mapped_column(Text)
    cancelado_por: Mapped[str | None] = mapped_column(String(26))
    cancelado_motivo: Mapped[str | None] = mapped_column(Text)
    lembrete_enviado: Mapped[bool] = mapped_column(Boolean, default=False)

    cliente: Mapped[Usuario] = relationship("Usuario", foreign_keys=[cliente_id])
    profissional: Mapped[Profissional] = relationship("Profissional")
    servico: Mapped[Servico] = relationship("Servico")
