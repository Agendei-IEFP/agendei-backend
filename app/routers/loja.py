from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import require_role
from app.db.session import get_db
from app.models.usuario import RoleEnum, Usuario
from app.schemas.loja import LojaCreate, LojaPublic, LojaUpdate
from app.services import loja_service

router = APIRouter(prefix="/lojas", tags=["lojas"])


@router.get("", response_model=list[LojaPublic])
async def listar_lojas(db: AsyncSession = Depends(get_db)):
    return await loja_service.listar_lojas(db)


@router.get("/{loja_id}", response_model=LojaPublic)
async def get_loja(loja_id: str, db: AsyncSession = Depends(get_db)):
    return await loja_service.get_loja(db, loja_id)


@router.post("", response_model=LojaPublic, status_code=201)
async def criar_loja(
    dados: LojaCreate,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(require_role(RoleEnum.admin_loja)),
):
    return await loja_service.criar_loja(db, dados, current_user.id)


@router.patch("/{loja_id}", response_model=LojaPublic)
async def atualizar_loja(
    loja_id: str,
    dados: LojaUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(require_role(RoleEnum.admin_loja)),
):
    return await loja_service.atualizar_loja(db, loja_id, dados, current_user)


@router.delete("/{loja_id}", status_code=204)
async def deletar_loja(
    loja_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(require_role(RoleEnum.admin_loja)),
):
    await loja_service.deletar_loja(db, loja_id, current_user)
