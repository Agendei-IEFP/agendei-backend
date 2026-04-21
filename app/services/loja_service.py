from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.loja import Loja
from app.models.usuario import Usuario
from app.schemas.loja import LojaCreate, LojaUpdate


async def listar_lojas(db: AsyncSession) -> list[Loja]:
    result = await db.execute(
        select(Loja).where(
            Loja.deleted_at.is_(None),
            Loja.is_active.is_(True),
        )
    )
    return result.scalars().all()


async def get_loja(db: AsyncSession, loja_id: str) -> Loja:
    result = await db.execute(
        select(Loja).where(Loja.id == loja_id, Loja.deleted_at.is_(None))
    )
    loja = result.scalar_one_or_none()
    if loja is None:
        raise HTTPException(status_code=404, detail="Loja não encontrada")
    return loja


async def criar_loja(db: AsyncSession, dados: LojaCreate, owner_id: str) -> Loja:
    loja = Loja(**dados.model_dump(), owner_id=owner_id)
    db.add(loja)
    await db.commit()
    await db.refresh(loja)
    return loja


async def atualizar_loja(
    db: AsyncSession,
    loja_id: str,
    dados: LojaUpdate,
    current_user: Usuario,
) -> Loja:
    loja = await get_loja(db, loja_id)
    if loja.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Acesso negado")
    for campo, valor in dados.model_dump(exclude_unset=True).items():
        setattr(loja, campo, valor)
    await db.commit()
    await db.refresh(loja)
    return loja


async def deletar_loja(
    db: AsyncSession,
    loja_id: str,
    current_user: Usuario,
) -> None:
    loja = await get_loja(db, loja_id)
    if loja.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Acesso negado")
    loja.deleted_at = datetime.now(timezone.utc)
    await db.commit()
