from datetime import datetime
from sqlalchemy import (
    String,
    Text,
    Integer,
    DateTime,
    ForeignKey,
    JSON
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.mixins import Base, ULIDMixin, TimestampMixin
from enum import Enum
from sqlalchemy import Enum as SAEnum

class NotificationType(str, Enum):
    reminder = "reminder"
    confirmation = "confirmation"
    cancellation = "cancellation"
    evaluation = "evaluation"


class RecipientType(str, Enum):
    customer = "customer"
    professional = "professional"


class NotificationChannel(str, Enum):
    email = "email"
    sms = "sms"
    whatsapp = "whatsapp"



class Notification(Base, ULIDMixin, TimestampMixin):
    __tablename__ = "notifications"

    notification_type: Mapped[NotificationType] = mapped_column(
    SAEnum(NotificationType),
    nullable=False
    ) # se é de marcação, cancelamento, avaliacao

    channel: Mapped[NotificationChannel] = mapped_column(
        SAEnum(NotificationType),
        nullable=False,
    ) # whats, email, etc

    recipient_id: Mapped[str] = mapped_column(
        String(26),
        nullable=False,
    ) # Quem vai receber a notificação

    recipient_type: Mapped[RecipientType] = mapped_column(
        SAEnum(RecipientType),
        nullable=False,
    ) # proficional ou customer

    appointment_id: Mapped[str | None] = mapped_column(
        String(26),
        ForeignKey("appointments.id", ondelete="SET NULL"),
        nullable=True,
    ) # Se for notificação específica

    title: Mapped[str | None] = mapped_column(
        String(120),
        nullable=True,
    ) # titulo da notificação, para caso de email

    message: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    ) # mensagem da notificação

    """payload: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
    ) # aqui é um JSON que pode conter dados mais específicos para economizar campos
    """
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="pending",
    ) # estatus

    attempts: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    ) # contador de tentativas de envio da notificaçao para o Worker

    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    ) # Registo do nome do erro do envio da mensagem, caso ocorra

    scheduled_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    ) # Data que será enviada a notificação

    sent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    ) # Data que realmente foi enviada

    # Relacionamento opcional
    appointment = relationship(
        "Appointment",
        back_populates="notifications"
    )
