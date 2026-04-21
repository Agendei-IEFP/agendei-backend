from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.usuario import Usuario, RoleEnum
from app.schemas.profissional import ProfissionalCreate, ProfissionalUpdate, ProfissionalPublic
from app.services import profissional_service
from app.core.dependencies import require_role

router = APIRouter(prefix="/lojas/{loja_id}/profissionais", tags=["profissionais"])


@router.post("/", response_model=ProfissionalPublic, status_code=status.HTTP_201_CREATED)
async def adicionar_profissional(
    loja_id: str,
    data: ProfissionalCreate,
    db: AsyncSession = Depends(get_db),
    admin: Usuario = Depends(require_role(RoleEnum.admin_loja)),
):
    """Adiciona um profissional a uma loja."""
    return await profissional_service.adicionar_profissional(db, loja_id, data, admin)


@router.get("/", response_model=list[ProfissionalPublic])
async def listar_profissionais(loja_id: str, db: AsyncSession = Depends(get_db)):
    """Lista profissionais de uma loja. Rota pública."""
    return await profissional_service.listar_profissionais_da_loja(db, loja_id)


@router.patch("/{profissional_id}", response_model=ProfissionalPublic)
async def atualizar_profissional(
    loja_id: str,
    profissional_id: str,
    data: ProfissionalUpdate,
    db: AsyncSession = Depends(get_db),
    admin: Usuario = Depends(require_role(RoleEnum.admin_loja)),
):
    return await profissional_service.atualizar_profissional(db, profissional_id, data, admin)


@router.delete("/{profissional_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remover_profissional(
    loja_id: str,
    profissional_id: str,
    db: AsyncSession = Depends(get_db),
    admin: Usuario = Depends(require_role(RoleEnum.admin_loja)),
):
    await profissional_service.remover_profissional(db, profissional_id, admin)