from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.offering import Offering
from app.models.professional import Professional
from app.models.professional_store import ProfessionalStore
from app.models.service import Service
from app.models.store import Store
from app.models.user import User
from app.schemas.offering import OfferingCreate, OfferingUpdate
from app.services.professional_service import get_professional_store
from app.services.service_service import get_service


async def _verify_owner(
    db: AsyncSession, professional_store_id: str, user: User
) -> ProfessionalStore:
    """
    Returns the active ProfessionalStore link if `user` may manage offerings on it.
    Allowed: the professional behind the link, or the store owner.
    """
    result = await db.execute(
        select(ProfessionalStore, Professional, Store)
        .join(Professional, Professional.id == ProfessionalStore.professional_id)
        .join(Store, Store.id == ProfessionalStore.store_id)
        .where(
            ProfessionalStore.id == professional_store_id,
            ProfessionalStore.deleted_at.is_(None),
        )
    )
    row = result.first()
    if row is None:
        raise HTTPException(
            status_code=404,
            detail="Vínculo profissional-loja não encontrado",
        )
    link, professional, store = row
    if professional.user_id != user.id and store.owner_id != user.id:
        raise HTTPException(status_code=403, detail="Acesso negado")
    return link


async def create_offering(
    db: AsyncSession,
    professional_store_id: str,
    data: OfferingCreate,
    user: User,
) -> Offering:
    link = await _verify_owner(db, professional_store_id, user)
    service = await get_service(db, data.service_id)

    # Ensure the service belongs to the professional of this link
    if service.professional_id != link.professional_id:
        raise HTTPException(
            status_code=422,
            detail="Este serviço não pertence ao profissional deste vínculo",
        )

    # Check for duplicate (same service already active on this link)
    existing = await db.execute(
        select(Offering).where(
            Offering.service_id == data.service_id,
            Offering.professional_store_id == professional_store_id,
            Offering.deleted_at.is_(None),
        )
    )
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=409,
            detail="Este serviço já está ativo nesta loja",
        )

    offering = Offering(
        service_id=data.service_id,
        professional_store_id=professional_store_id,
        price_override=data.price_override,
        duration_override=data.duration_override,
    )
    db.add(offering)
    await db.commit()
    await db.refresh(offering)

    result = await db.execute(
        select(Offering)
        .options(selectinload(Offering.service))
        .where(Offering.id == offering.id)
    )
    return result.scalar_one()


async def list_professional_store_offerings(
    db: AsyncSession, professional_store_id: str
) -> list[Offering]:
    await get_professional_store(db, professional_store_id)
    result = await db.execute(
        select(Offering)
        .options(selectinload(Offering.service))
        .join(Service, Service.id == Offering.service_id)
        .where(
            Offering.professional_store_id == professional_store_id,
            Offering.deleted_at.is_(None),
            Service.deleted_at.is_(None),
            Service.is_active.is_(True),
        )
    )
    return list(result.scalars().all())


async def get_offering(db: AsyncSession, offering_id: str) -> Offering:
    result = await db.execute(
        select(Offering)
        .options(selectinload(Offering.service))
        .where(
            Offering.id == offering_id,
            Offering.deleted_at.is_(None),
        )
    )
    offering = result.scalar_one_or_none()
    if offering is None:
        raise HTTPException(status_code=404, detail="Serviço não encontrado")
    return offering


async def update_offering(
    db: AsyncSession,
    offering_id: str,
    data: OfferingUpdate,
    user: User,
) -> Offering:
    offering = await get_offering(db, offering_id)
    await _verify_owner(db, offering.professional_store_id, user)

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(offering, field, value)

    await db.commit()

    result = await db.execute(
        select(Offering)
        .options(selectinload(Offering.service))
        .where(Offering.id == offering_id)
    )
    return result.scalar_one()


async def delete_offering(
    db: AsyncSession, offering_id: str, user: User
) -> None:
    offering = await get_offering(db, offering_id)
    await _verify_owner(db, offering.professional_store_id, user)

    offering.deleted_at = datetime.now(timezone.utc)
    await db.commit()
