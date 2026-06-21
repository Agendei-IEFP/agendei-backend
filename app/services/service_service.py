from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.service import Service
from app.models.user import User
from app.schemas.service import ServiceCreate, ServiceUpdate
from app.services import professional_service


async def _get_professional_for_user(db: AsyncSession, user: User):
    return await professional_service.get_my_profile(db, user)


async def get_service(db: AsyncSession, service_id: str) -> Service:
    result = await db.execute(
        select(Service).where(
            Service.id == service_id,
            Service.deleted_at.is_(None),
        )
    )
    service = result.scalar_one_or_none()
    if service is None:
        raise HTTPException(status_code=404, detail="Serviço não encontrado")
    return service


async def create_service(db: AsyncSession, data: ServiceCreate, user: User) -> Service:
    professional = await _get_professional_for_user(db, user)

    service = Service(
        professional_id=professional.id,
        name=data.name,
        description=data.description,
        price=data.price,
        duration_minutes=data.duration_minutes,
    )
    db.add(service)
    await db.commit()
    await db.refresh(service)
    return service


async def list_my_services(db: AsyncSession, user: User) -> list[Service]:
    professional = await _get_professional_for_user(db, user)

    result = await db.execute(
        select(Service).where(
            Service.professional_id == professional.id,
            Service.deleted_at.is_(None),
        )
    )
    return list(result.scalars().all())


async def update_service(
        db: AsyncSession, service_id: str, data: ServiceUpdate, user: User
) -> Service:
    service = await get_service(db, service_id)
    professional = await _get_professional_for_user(db, user)

    if service.professional_id != professional.id:
        raise HTTPException(status_code=403, detail="Acesso negado")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(service, field, value)

    await db.commit()
    await db.refresh(service)
    return service


async def delete_service(db: AsyncSession, service_id: str, user: User) -> None:
    service = await get_service(db, service_id)
    professional = await _get_professional_for_user(db, user)

    if service.professional_id != professional.id:
        raise HTTPException(status_code=403, detail="Acesso negado")

    service.deleted_at = datetime.now(timezone.utc)
    await db.commit()
