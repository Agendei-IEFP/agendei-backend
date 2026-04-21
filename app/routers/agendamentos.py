from datetime import date
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.usuario import Usuario, RoleEnum
from app.schemas.agendamento import AgendamentoCreate, AgendamentoUpdate, AgendamentoPublic, SlotDisponivel
from app.services import agendamento_service
from app.core.dependencies import get_current_user, require_role

router = APIRouter(prefix="/agendamentos", tags=["agendamentos"])


@router.get("/slots", response_model=list[SlotDisponivel])
async def slots_disponiveis(
    profissional_id: str = Query(..., description="ID do profissional"),
    servico_id: str = Query(..., description="ID do serviço"),
    data: date = Query(..., description="Data no formato YYYY-MM-DD"),
    db: AsyncSession = Depends(get_db),
):
    """
    Retorna os horários disponíveis para agendamento.
    Rota pública — o cliente consulta antes de logar.

    Exemplo: GET /agendamentos/slots?profissional_id=...&servico_id=...&data=2025-08-15
    """
    return await agendamento_service.listar_slots_disponiveis(
        db, profissional_id, servico_id, data
    )


@router.post("/", response_model=AgendamentoPublic, status_code=status.HTTP_201_CREATED)
async def criar_agendamento(
    data: AgendamentoCreate,
    db: AsyncSession = Depends(get_db),
    cliente: Usuario = Depends(get_current_user),
):
    """
    Cria um agendamento. O cliente deve estar autenticado.
    O ID do cliente vem do token, não do body — evita agendamentos no nome de outros.
    """
    return await agendamento_service.criar_agendamento(db, data, cliente)


@router.get("/meus", response_model=list[AgendamentoPublic])
async def meus_agendamentos(
    db: AsyncSession = Depends(get_db),
    cliente: Usuario = Depends(get_current_user),
):
    """Lista os agendamentos do cliente autenticado."""
    return await agendamento_service.listar_agendamentos_do_cliente(db, cliente)


@router.get("/profissional/{profissional_id}", response_model=list[AgendamentoPublic])
async def agendamentos_do_profissional(
    profissional_id: str,
    db: AsyncSession = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
):
    """
    Lista agendamentos de um profissional.
    Acessível pelo próprio profissional ou pelo admin da loja.
    """
    return await agendamento_service.listar_agendamentos_do_profissional(
        db, profissional_id, usuario
    )


@router.patch("/{agendamento_id}/status", response_model=AgendamentoPublic)
async def atualizar_status(
    agendamento_id: str,
    data: AgendamentoUpdate,
    db: AsyncSession = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
):
    """
    Atualiza o status de um agendamento.
    Transições válidas:
      pendente → confirmado (profissional/admin)
      pendente → cancelado (qualquer um dos três)
      confirmado → concluido (profissional/admin)
      confirmado → cancelado (qualquer um dos três)
    """
    return await agendamento_service.atualizar_status(db, agendamento_id, data, usuario)