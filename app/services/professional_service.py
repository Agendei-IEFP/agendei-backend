from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.professional import Professional
from app.models.professional_store import ProfessionalStore
from app.models.user import User
from app.schemas.professional import ProfessionalSelfCreate, ProfessionalUpdate
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


async def get_professional_store(
    db: AsyncSession, professional_store_id: str
) -> ProfessionalStore:
    result = await db.execute(
        select(ProfessionalStore).where(
            ProfessionalStore.id == professional_store_id,
            ProfessionalStore.deleted_at.is_(None),
        )
    )
    link = result.scalar_one_or_none()
    if link is None:
        raise HTTPException(status_code=404, detail="Vínculo profissional-loja não encontrado")
    return link


async def add_admin_as_professional(
    db: AsyncSession,
    store_id: str,
    data: ProfessionalSelfCreate,
    admin: User,
) -> ProfessionalStore:
    store = await get_store(db, store_id)

    if store.owner_id != admin.id:
        raise HTTPException(status_code=403, detail="Apenas o dono da loja pode se vincular como profissional")

    # Guarantee the Professional record exists (1:1 with user)
    result = await db.execute(
        select(Professional).where(
            Professional.user_id == admin.id,
            Professional.deleted_at.is_(None),
        )
    )
    professional = result.scalar_one_or_none()
    if professional is None:
        professional = Professional(
            user_id=admin.id,
            bio=data.bio,
            photo_url=data.photo_url,
        )
        db.add(professional)
        await db.flush()
    else:
        if data.bio is not None:
            professional.bio = data.bio
        if data.photo_url is not None:
            professional.photo_url = data.photo_url

    # Create or reactivate the ProfessionalStore link (including soft-deleted)
    result = await db.execute(
        select(ProfessionalStore).where(
            ProfessionalStore.professional_id == professional.id,
            ProfessionalStore.store_id == store_id,
        )
    )
    link = result.scalar_one_or_none()

    if link is not None and link.deleted_at is None:
        raise HTTPException(status_code=409, detail="Você já é profissional desta loja")

    if link is not None:
        # Reactivate soft-deleted link
        link.deleted_at = None
        link.is_active = True
    else:
        link = ProfessionalStore(
            professional_id=professional.id,
            store_id=store_id,
        )
        db.add(link)

    await db.commit()
    await db.refresh(link)
    return link


async def list_store_professionals(
    db: AsyncSession, store_id: str
) -> list[Professional]:
    await get_store(db, store_id)
    result = await db.execute(
        select(Professional)
        .join(
            ProfessionalStore,
            ProfessionalStore.professional_id == Professional.id,
        )
        .where(
            ProfessionalStore.store_id == store_id,
            ProfessionalStore.deleted_at.is_(None),
            ProfessionalStore.is_active.is_(True),
            Professional.deleted_at.is_(None),
        )
    )
    return list(result.scalars().all())


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

    # Verify professional is linked to this store
    result = await db.execute(
        select(ProfessionalStore).where(
            ProfessionalStore.professional_id == professional.id,
            ProfessionalStore.store_id == store_id,
            ProfessionalStore.deleted_at.is_(None),
        )
    )
    if result.scalar_one_or_none() is None:
        raise HTTPException(status_code=404, detail="Profissional não encontrado nesta loja")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(professional, field, value)

    await db.commit()
    await db.refresh(professional)
    return professional


async def unlink_professional_from_store(
    db: AsyncSession, professional_store_id: str, admin: User
) -> None:
    link = await get_professional_store(db, professional_store_id)
    store = await get_store(db, link.store_id)

    if store.owner_id != admin.id:
        raise HTTPException(status_code=403, detail="Apenas o dono da loja pode desvincular profissionais")

    link.deleted_at = datetime.now(timezone.utc)
    await db.commit()


async def list_user_professional_stores(
    db: AsyncSession, user: User
) -> list[ProfessionalStore]:
    result = await db.execute(
        select(Professional).where(
            Professional.user_id == user.id,
            Professional.deleted_at.is_(None),
        )
    )
    professional = result.scalar_one_or_none()
    if professional is None:
        return []

    result = await db.execute(
        select(ProfessionalStore).where(
            ProfessionalStore.professional_id == professional.id,
            ProfessionalStore.deleted_at.is_(None),
            ProfessionalStore.is_active.is_(True),
        )
    )
    return list(result.scalars().all())
