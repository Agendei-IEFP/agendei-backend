from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.usuario import Usuario, RoleEnum
from app.schemas.loja import LojaCreate, LojaUpdate, LojaPublic
from app.services import loja_service
from app.core.dependencies import get_current_user, require_role

router = APIRouter(prefix="/lojas", tags=["lojas"])


@router.post("/", response_model=LojaPublic, status_code=status.HTTP_201_CREATED)
async def criar_loja(
    data: LojaCreate,
    db: AsyncSession = Depends(get_db),
    usuario: Usuario = Depends(require_role(RoleEnum.admin_loja)),
):
    """Cria uma nova loja. Requer autenticação com role=admin_loja."""
    return await loja_service.criar_loja(db, data, usuario)


@router.get("/", response_model=list[LojaPublic])
async def listar_lojas(db: AsyncSession = Depends(get_db)):
    """Lista todas as lojas ativas. Rota pública."""
    return await loja_service.listar_lojas(db)


@router.get("/{loja_id}", response_model=LojaPublic)
async def buscar_loja(loja_id: str, db: AsyncSession = Depends(get_db)):
    """Busca uma loja pelo ID. Rota pública."""
    return await loja_service.buscar_loja(db, loja_id)


@router.patch("/{loja_id}", response_model=LojaPublic)
async def atualizar_loja(
    loja_id: str,
    data: LojaUpdate,
    db: AsyncSession = Depends(get_db),
    usuario: Usuario = Depends(require_role(RoleEnum.admin_loja)),
):
    """Atualiza campos de uma loja. Só o dono pode editar."""
    return await loja_service.atualizar_loja(db, loja_id, data, usuario)


@router.delete("/{loja_id}", status_code=status.HTTP_204_NO_CONTENT)
async def deletar_loja(
    loja_id: str,
    db: AsyncSession = Depends(get_db),
    usuario: Usuario = Depends(require_role(RoleEnum.admin_loja)),
):
    """Soft delete de uma loja. Só o dono pode deletar."""
    await loja_service.deletar_loja(db, loja_id, usuario)