from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException

from app.models.profissional import Profissional
from app.models.usuario import Usuario, RoleEnum
from app.schemas.profissional import ProfissionalCreate, ProfissionalUpdate
from app.services.loja_service import buscar_loja


async def adicionar_profissional(
    db: AsyncSession,
    loja_id: str,
    data: ProfissionalCreate,
    admin: Usuario,
) -> Profissional:
    """
    Adiciona um profissional a uma loja.
    Só o dono da loja pode fazer isso.
    O usuário referenciado deve ter role=profissional.
    """
    loja = await buscar_loja(db, loja_id)

    if loja.owner_id != admin.id:
        raise HTTPException(status_code=403, detail="Apenas o dono da loja pode adicionar profissionais")

    # Verifica se o usuário existe e tem o papel correto
    result = await db.execute(
        select(Usuario).where(
            Usuario.id == data.usuario_id,
            Usuario.deleted_at.is_(None),
        )
    )
    usuario = result.scalar_one_or_none()
    if usuario is None:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    if usuario.role != RoleEnum.profissional:
        raise HTTPException(status_code=422, detail="O usuário deve ter role=profissional")

    # Verifica se já está cadastrado nesta loja
    ja_existe = await db.execute(
        select(Profissional).where(
            Profissional.usuario_id == data.usuario_id,
            Profissional.loja_id == loja_id,
            Profissional.deleted_at.is_(None),
        )
    )
    if ja_existe.scalar_one_or_none() is not None:
        raise HTTPException(status_code=409, detail="Profissional já cadastrado nesta loja")

    profissional = Profissional(
        usuario_id=data.usuario_id,
        loja_id=loja_id,
        bio=data.bio,
        foto_url=data.foto_url,
    )
    db.add(profissional)
    await db.commit()
    await db.refresh(profissional)
    return profissional


async def listar_profissionais_da_loja(
    db: AsyncSession, loja_id: str
) -> list[Profissional]:
    """Lista os profissionais ativos de uma loja. Rota pública."""
    await buscar_loja(db, loja_id)  # garante que a loja existe
    result = await db.execute(
        select(Profissional).where(
            Profissional.loja_id == loja_id,
            Profissional.deleted_at.is_(None),
            Profissional.is_active.is_(True),
        )
    )
    return list(result.scalars().all())


async def buscar_profissional(db: AsyncSession, profissional_id: str) -> Profissional:
    result = await db.execute(
        select(Profissional).where(
            Profissional.id == profissional_id,
            Profissional.deleted_at.is_(None),
        )
    )
    profissional = result.scalar_one_or_none()
    if profissional is None:
        raise HTTPException(status_code=404, detail="Profissional não encontrado")
    return profissional


async def atualizar_profissional(
    db: AsyncSession,
    profissional_id: str,
    data: ProfissionalUpdate,
    admin: Usuario,
) -> Profissional:
    profissional = await buscar_profissional(db, profissional_id)
    loja = await buscar_loja(db, profissional.loja_id)

    if loja.owner_id != admin.id:
        raise HTTPException(status_code=403, detail="Apenas o dono da loja pode editar profissionais")

    campos = data.model_dump(exclude_unset=True)
    for campo, valor in campos.items():
        setattr(profissional, campo, valor)

    await db.commit()
    await db.refresh(profissional)
    return profissional


async def remover_profissional(
    db: AsyncSession, profissional_id: str, admin: Usuario
) -> None:
    from datetime import datetime, timezone

    profissional = await buscar_profissional(db, profissional_id)
    loja = await buscar_loja(db, profissional.loja_id)

    if loja.owner_id != admin.id:
        raise HTTPException(status_code=403, detail="Apenas o dono da loja pode remover profissionais")

    profissional.deleted_at = datetime.now(timezone.utc)
    await db.commit()