"""
appointment_service.py — Agendei
Adiciona ao serviço existente:
  • Paginação
  • Filtros por data e status
  • Anonimização GDPR
"""

from datetime import date
from typing import Optional, List, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.appointment import Appointment
from app.models.user import User
from app.schemas.pagination import PagedResponse


# ---------------------------------------------------------------------------
# Helpers internos
# ---------------------------------------------------------------------------

def _apply_appointment_filters(
    query,
    data_inicio: Optional[date],
    data_fim: Optional[date],
    status: Optional[str],
    user_id: Optional[int],
):
    """Aplica filtros opcionais à query de agendamentos."""
    if data_inicio:
        query = query.filter(Appointment.date >= data_inicio)
    if data_fim:
        query = query.filter(Appointment.date <= data_fim)
    if status:
        query = query.filter(Appointment.status == status)
    if user_id:
        query = query.filter(Appointment.user_id == user_id)
    return query


# ---------------------------------------------------------------------------
# Listar agendamentos com paginação + filtros
# ---------------------------------------------------------------------------

def get_appointments_paginated(
    db: Session,
    page: int = 1,
    page_size: int = 20,
    data_inicio: Optional[date] = None,
    data_fim: Optional[date] = None,
    status: Optional[str] = None,
    user_id: Optional[int] = None,
) -> PagedResponse:
    """
    Devolve uma página de agendamentos com filtros opcionais.

    Parâmetros
    ----------
    page        : página pedida (começa em 1)
    page_size   : itens por página (máx. 100)
    data_inicio : filtrar a partir desta data (inclusive)
    data_fim    : filtrar até esta data (inclusive)
    status      : pendente | confirmado | cancelado | concluido
    user_id     : restringir a um utilizador específico
    """
    query = db.query(Appointment)
    query = _apply_appointment_filters(query, data_inicio, data_fim, status, user_id)

    total: int = query.with_entities(func.count(Appointment.id)).scalar()

    offset = (page - 1) * page_size
    items: List[Appointment] = (
        query
        .order_by(Appointment.date.desc())
        .offset(offset)
        .limit(page_size)
        .all()
    )

    return PagedResponse.create(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
    )


# ---------------------------------------------------------------------------
# GDPR — Anonimização / Apagamento de dados pessoais
# ---------------------------------------------------------------------------

GDPR_ANONYMOUS_NAME  = "Utilizador Anonimizado"
GDPR_ANONYMOUS_EMAIL = "anonimo@apagado.invalid"
GDPR_ANONYMOUS_PHONE = "000000000"


def anonymize_user_gdpr(db: Session, user_id: int) -> dict:
    """
    Anonimiza todos os dados pessoais de um utilizador (RGPD Art.º 17).

    O que é apagado / substituído
    ------------------------------
    • name / full_name  → GDPR_ANONYMOUS_NAME
    • email             → endereço inválido único
    • phone             → zeros
    • password_hash     → string vazia (login fica impossível)
    • Agendamentos      → notas pessoais apagadas

    O registo e o histórico de agendamentos mantêm-se para integridade
    operacional, mas sem qualquer dado identificável.
    """
    user: Optional[User] = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise ValueError(f"Utilizador {user_id} não encontrado.")

    campos_apagados = []

    # — Dados do utilizador —
    if hasattr(user, "name"):
        user.name = GDPR_ANONYMOUS_NAME
        campos_apagados.append("name")

    if hasattr(user, "full_name"):
        user.full_name = GDPR_ANONYMOUS_NAME
        campos_apagados.append("full_name")

    if hasattr(user, "email"):
        # email único para não violar constraints UNIQUE
        user.email = f"anonimo_{user_id}@apagado.invalid"
        campos_apagados.append("email")

    if hasattr(user, "phone"):
        user.phone = GDPR_ANONYMOUS_PHONE
        campos_apagados.append("phone")

    if hasattr(user, "password_hash"):
        user.password_hash = ""
        campos_apagados.append("password_hash")

    if hasattr(user, "avatar_url"):
        user.avatar_url = None
        campos_apagados.append("avatar_url")

    if hasattr(user, "is_active"):
        user.is_active = False
        campos_apagados.append("is_active")

    # — Notas pessoais nos agendamentos —
    appointments = db.query(Appointment).filter(Appointment.user_id == user_id).all()
    if appointments:
        for appt in appointments:
            if hasattr(appt, "notes"):
                appt.notes = None
        campos_apagados.append(f"notes em {len(appointments)} agendamento(s)")

    db.commit()

    return {
        "mensagem": "Dados pessoais anonimizados com sucesso (RGPD Art.º 17).",
        "utilizador_id": user_id,
        "campos_apagados": campos_apagados,
    }
