from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from fastapi import HTTPException
from app.models.offering import Offering
from app.models.user import User
from app.schemas.offering import OfferingCreate, OfferingUpdate
from app.services.professional_service import get_professional_store
from app.services.service_service import get_service
from app.services.schedule_helper import verify_schedule_owner  # Reutiliza a mesma verificação de permissão!


async def get_offering(db: AsyncSession, offering_id: str) -> Offering:
    result = await db.execute(
        select(Offering).options(selectinload(Offering.service))
        .where(Offering.id == offering_id, Offering.deleted_at.is_(None))
    )
    offering = result.scalar_one_or_none()
    if not offering:
        raise HTTPException(status_code=404, detail="Serviço não encontrado")
    return offering


async def create_offering(db: AsyncSession, professional_store_id: str, data: OfferingCreate, user: User) -> Offering:
    await verify_schedule_owner(db, professional_store_id, user)
    await get_service(db, data.service_id)

    offering = Offering(professional_store_id=professional_store_id, **data.model_dump())
    db.add(offering)
    await db.commit()

    # Recarrega com os relacionamentos necessários para o schema de saída
    return await get_offering(db, offering.id)


async def update_offering(db: AsyncSession, offering_id: str, data: OfferingUpdate, user: User) -> Offering:
    offering = await get_offering(db, offering_id)
    await verify_schedule_owner(db, offering.professional_store_id, user)

    # Atualização limpa numa só linha
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(offering, field, value)

    await db.commit()
    return await get_offering(db, offering_id)