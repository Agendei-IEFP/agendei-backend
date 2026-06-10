from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.professional import Professional
from app.models.store import Store
from app.models.user import User
from app.schemas.professional import ProfessionalSelfCreate, ProfessionalUpdate, ProfessionalWithNamePublic
from app.services.store_service import get_store


async def get_professional(db: AsyncSession, professional_id: str) -> Professional:
    result = await db.execute(
        select(Professional).where(
            Professional.id == professional_id,
            Professional.deleted_at.is_(None),
        )
    )
    professional = result.scalar_one_or_none()
    if professional is None:
        raise HTTPException(status_code=404, detail="Profissional não encontrado")
    return professional


async def add_admin_as_professional(
    db: AsyncSession,
    store_id: str,
    data: ProfessionalSelfCreate,
    admin: User,
) -> Professional:
    store = await get_store(db, store_id)

    if store.owner_id != admin.id:
        raise HTTPException(status_code=403, detail="Apenas o dono da loja pode se vincular como profissional")

    result = await db.execute(
        select(Professional).where(
            Professional.user_id == admin.id,
            Professional.deleted_at.is_(None),
        )
    )
    professional = result.scalar_one_or_none()

    if professional is not None:
        if professional.store_id == store_id:
            raise HTTPException(status_code=409, detail="Você já é profissional desta loja")
        raise HTTPException(status_code=409, detail="Você já é profissional de outra loja")

    professional = Professional(
        user_id=admin.id,
        store_id=store_id,
        bio=data.bio,
        photo_url=data.photo_url,
    )
    db.add(professional)
    await db.commit()

    result = await db.execute(
        select(Professional)
        .options(selectinload(Professional.store))
        .where(Professional.id == professional.id)
    )
    return result.scalar_one()


async def list_store_professionals(
    db: AsyncSession, store_id: str
) -> list[Professional]:
    await get_store(db, store_id)
    result = await db.execute(
        select(Professional).where(
            Professional.store_id == store_id,
            Professional.deleted_at.is_(None),
            Professional.is_active.is_(True),
        )
    )
    return list(result.scalars().all())


async def list_store_professionals_with_name(
    db: AsyncSession, store_id: str
) -> list[ProfessionalWithNamePublic]:
    await get_store(db, store_id)
    result = await db.execute(
        select(Professional)
        .options(selectinload(Professional.user))
        .where(
            Professional.store_id == store_id,
            Professional.deleted_at.is_(None),
            Professional.is_active.is_(True),
        )
    )
    professionals = result.scalars().all()
    return [
        ProfessionalWithNamePublic(
            id=p.id,
            user_id=p.user_id,
            store_id=p.store_id,
            name=p.user.name,
            bio=p.bio,
            photo_url=p.photo_url,
            is_active=p.is_active,
        )
        for p in professionals
    ]


async def update_professional(
    db: AsyncSession,
    store_id: str,
    professional_id: str,
    data: ProfessionalUpdate,
    admin: User,
) -> Professional:
    store = await get_store(db, store_id)

    if store.owner_id != admin.id:
        raise HTTPException(status_code=403, detail="Apenas o dono da loja pode editar profissionais")

    professional = await get_professional(db, professional_id)

    if professional.store_id != store_id:
        raise HTTPException(status_code=404, detail="Profissional não encontrado nesta loja")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(professional, field, value)

    await db.commit()
    await db.refresh(professional)
    return professional


async def unlink_professional_from_store(
    db: AsyncSession, professional_id: str, store_id: str, admin: User
) -> None:
    store = await get_store(db, store_id)

    if store.owner_id != admin.id:
        raise HTTPException(status_code=403, detail="Apenas o dono da loja pode desvincular profissionais")

    professional = await get_professional(db, professional_id)

    if professional.store_id != store_id:
        raise HTTPException(status_code=404, detail="Profissional não encontrado nesta loja")

    professional.deleted_at = datetime.now(timezone.utc)
    await db.commit()


async def list_my_professional_stores(
    db: AsyncSession, user: User
) -> list[Professional]:
    result = await db.execute(
        select(Professional)
        .options(selectinload(Professional.store), selectinload(Professional.user))
        .where(
            Professional.user_id == user.id,
            Professional.deleted_at.is_(None),
        )
    )
    return list(result.scalars().all())


async def get_my_profile(db: AsyncSession, user: User) -> Professional:
    result = await db.execute(
        select(Professional).where(
            Professional.user_id == user.id,
            Professional.deleted_at.is_(None),
        )
    )
    professional = result.scalar_one_or_none()
    if professional is None:
        raise HTTPException(status_code=404, detail="Perfil de profissional não encontrado")
    return professional


async def update_my_profile(
    db: AsyncSession, data: ProfessionalUpdate, user: User
) -> Professional:
    professional = await get_my_profile(db, user)

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(professional, field, value)

    await db.commit()
    await db.refresh(professional)
    return professional


async def list_my_professionals(
    db: AsyncSession, admin: User
) -> list[Professional]:
    result = await db.execute(
        select(Professional)
        .options(selectinload(Professional.user), selectinload(Professional.store))
        .join(Store, Store.id == Professional.store_id)
        .where(
            Store.owner_id == admin.id,
            Store.deleted_at.is_(None),
            Professional.deleted_at.is_(None),
        )
    )
    return list(result.scalars().all())
