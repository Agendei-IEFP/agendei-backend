from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.models.profissional import Profissional
from app.models.usuario import Usuario, RoleEnum
from app.schemas.profissional import ProfissionalCreate, ProfissionalUpdate
from app.services.loja_service import get_loja


async def adicionar_profissional(
    db: AsyncSession,
    loja_id: str,
    data: ProfissionalCreate,
    admin: Usuario,
) -> Profissional:
    loja = await get_loja(db, loja_id)

    if loja.owner_id != admin.id:
        raise HTTPException(status_code=403, detail="Apenas o dono da loja pode adicionar profissionais")

    existing = await db.execute(
        select(Usuario).where(Usuario.email == data.email, Usuario.deleted_at.is_(None))
    )
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(status_code=409, detail="Email já cadastrado")

    usuario = Usuario(
        nome=data.nome,
        email=data.email,
        senha_hash=hash_password(data.senha),
        role=RoleEnum.profissional,
    )
    db.add(usuario)
    await db.flush()

    profissional = Profissional(
        usuario_id=usuario.id,
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
    await get_loja(db, loja_id)  # garante que a loja existe
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
    loja = await get_loja(db, profissional.loja_id)

    if loja.owner_id != admin.id:
        raise HTTPException(status_code=403, detail="Apenas o dono da loja pode editar profissionais")

    for campo, valor in data.model_dump(exclude_unset=True).items():
        setattr(profissional, campo, valor)

    await db.commit()
    await db.refresh(profissional)
    return profissional


async def remover_profissional(
    db: AsyncSession, profissional_id: str, admin: Usuario
) -> None:
    profissional = await buscar_profissional(db, profissional_id)
    loja = await get_loja(db, profissional.loja_id)

    if loja.owner_id != admin.id:
        raise HTTPException(status_code=403, detail="Apenas o dono da loja pode remover profissionais")

    profissional.deleted_at = datetime.now(timezone.utc)
    await db.commit()
