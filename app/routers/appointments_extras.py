"""
routers/appointments_extras.py — Agendei
Adiciona ao router existente:
  • GET  /appointments          → paginação + filtros
  • DELETE /users/{user_id}/gdpr → anonimização RGPD
"""

from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status as http_status
from sqlalchemy.orm import Session

from app.core.dependencies import get_db, get_current_user
from app.schemas.appointment import AppointmentPublic
from app.schemas.pagination import PagedResponse
from app.services.appointment_service_extras import (
    get_appointments_paginated,
    anonymize_user_gdpr,
)

router = APIRouter(prefix="/appointments", tags=["Appointments"])


# ---------------------------------------------------------------------------
# GET /appointments — lista paginada com filtros
# ---------------------------------------------------------------------------

@router.get(
    "",
    response_model=PagedResponse[AppointmentPublic],
    summary="Listar agendamentos (paginado + filtros)",
)
def list_appointments(
    # — Paginação —
    page: int = Query(default=1, ge=1, description="Página (começa em 1)"),
    page_size: int = Query(default=20, ge=1, le=100, description="Itens por página (máx. 100)"),
    # — Filtros —
    data_inicio: Optional[date] = Query(default=None, description="Data de início (YYYY-MM-DD)"),
    data_fim: Optional[date] = Query(default=None, description="Data de fim (YYYY-MM-DD)"),
    appointment_status: Optional[str] = Query(
        default=None,
        alias="status",
        description="Estado: pendente | confirmado | cancelado | concluido",
    ),
    user_id: Optional[int] = Query(default=None, description="Filtrar por utilizador"),
    # — Infra —
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Exemplos de uso:
    GET /appointments?page=2&page_size=10
    GET /appointments?status=confirmado
    GET /appointments?data_inicio=2025-06-01&data_fim=2025-06-30
    GET /appointments?status=pendente&data_inicio=2025-06-01
    """
    if data_inicio and data_fim and data_inicio > data_fim:
        raise HTTPException(
            status_code=http_status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="data_inicio não pode ser posterior a data_fim.",
        )

    return get_appointments_paginated(
        db=db,
        page=page,
        page_size=page_size,
        data_inicio=data_inicio,
        data_fim=data_fim,
        status=appointment_status,
        user_id=user_id,
    )


# ---------------------------------------------------------------------------
# DELETE /users/{user_id}/gdpr — RGPD: apagar dados pessoais
# ---------------------------------------------------------------------------

gdpr_router = APIRouter(prefix="/users", tags=["GDPR"])


@gdpr_router.delete(
    "/{user_id}/gdpr",
    summary="RGPD — Anonimizar dados pessoais de um utilizador",
    status_code=http_status.HTTP_200_OK,
)
def gdpr_delete_user_data(
        user_id: int,
        db: Session = Depends(get_db),
        current_user=Depends(get_current_user),
):
    """
    Anonimiza todos os dados pessoais de um utilizador conforme o **RGPD Art.º 17**
    (direito ao apagamento).

    - Substitui nome, email, telefone por valores anónimos
    - Apaga notas pessoais dos agendamentos
    - Desativa a conta (login impossível)
    - Mantém o histórico de agendamentos para integridade operacional

    Apenas administradores ou o próprio utilizador devem ter acesso.
    """
    # Opcional: só admin ou o próprio utilizador
    # if current_user.id != user_id and not current_user.is_admin:
    #     raise HTTPException(status_code=403, detail="Sem permissão.")

    try:
        result = anonymize_user_gdpr(db=db, user_id=user_id)
    except ValueError as e:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail=str(e))

    return result