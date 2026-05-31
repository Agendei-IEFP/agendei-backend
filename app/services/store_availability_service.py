from datetime import datetime, time, timezone

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.professional import Professional
from app.models.professional_store import ProfessionalStore
from app.models.store import Store
from app.models.store_availability import StoreAvailability
from app.models.user import User
from app.schemas.store_availability import StoreAvailabilityBulkReplace, StoreAvailabilityCreate, StoreAvailabilityUpdate
from app.services.professional_service import get_professional_store


async def _verify_owner(
    db: AsyncSession, professional_store_id: str, user: User
) -> ProfessionalStore:
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


async def _assert_no_overlap(
    db: AsyncSession,
    professional_store_id: str,
    weekday: int,
    start_time: time,
    end_time: time,
    exclude_id: str | None = None,
) -> None:
    q = select(StoreAvailability).where(
        StoreAvailability.professional_store_id == professional_store_id,
        StoreAvailability.weekday == weekday,
        StoreAvailability.deleted_at.is_(None),
        StoreAvailability.start_time < end_time,
        StoreAvailability.end_time > start_time,
    )
    if exclude_id is not None:
        q = q.where(StoreAvailability.id != exclude_id)
    result = await db.execute(q)
    if result.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=409,
            detail="O bloco se sobrepõe a um override existente neste dia para esta loja",
        )


async def list_store_availability(
    db: AsyncSession, professional_store_id: str
) -> list[StoreAvailability]:
    await get_professional_store(db, professional_store_id)
    result = await db.execute(
        select(StoreAvailability)
        .where(
            StoreAvailability.professional_store_id == professional_store_id,
            StoreAvailability.deleted_at.is_(None),
        )
        .order_by(StoreAvailability.weekday, StoreAvailability.start_time)
    )
    return list(result.scalars().all())


async def get_store_availability(
    db: AsyncSession, availability_id: str
) -> StoreAvailability:
    result = await db.execute(
        select(StoreAvailability).where(
            StoreAvailability.id == availability_id,
            StoreAvailability.deleted_at.is_(None),
        )
    )
    availability = result.scalar_one_or_none()
    if availability is None:
        raise HTTPException(status_code=404, detail="Override de disponibilidade não encontrado")
    return availability


async def create_store_availability(
    db: AsyncSession,
    professional_store_id: str,
    data: StoreAvailabilityCreate,
    user: User,
) -> StoreAvailability:
    await _verify_owner(db, professional_store_id, user)
    await _assert_no_overlap(
        db, professional_store_id, data.weekday, data.start_time, data.end_time
    )

    availability = StoreAvailability(
        professional_store_id=professional_store_id,
        weekday=data.weekday,
        start_time=data.start_time,
        end_time=data.end_time,
    )
    db.add(availability)
    await db.commit()
    await db.refresh(availability)
    return availability


async def update_store_availability(
    db: AsyncSession,
    availability_id: str,
    data: StoreAvailabilityUpdate,
    user: User,
) -> StoreAvailability:
    availability = await get_store_availability(db, availability_id)
    await _verify_owner(db, availability.professional_store_id, user)

    updates = data.model_dump(exclude_unset=True)
    if "start_time" in updates or "end_time" in updates:
        new_start = updates.get("start_time", availability.start_time)
        new_end = updates.get("end_time", availability.end_time)
        await _assert_no_overlap(
            db,
            availability.professional_store_id,
            availability.weekday,
            new_start,
            new_end,
            exclude_id=availability_id,
        )

    for field, value in updates.items():
        setattr(availability, field, value)

    await db.commit()
    await db.refresh(availability)
    return availability


async def delete_store_availability(
    db: AsyncSession, availability_id: str, user: User
) -> None:
    availability = await get_store_availability(db, availability_id)
    await _verify_owner(db, availability.professional_store_id, user)
    availability.deleted_at = datetime.now(timezone.utc)
    await db.commit()


async def replace_availability(
    db: AsyncSession,
    professional_store_id: str,
    data: StoreAvailabilityBulkReplace,
    user: User,
) -> list[StoreAvailability]:
    await _verify_owner(db, professional_store_id, user)

    # Validate overlaps within the incoming payload itself
    seen: dict[int, list[tuple[time, time]]] = {}
    for block in data.blocks:
        intervals = seen.setdefault(block.weekday, [])
        for existing_start, existing_end in intervals:
            if block.start_time < existing_end and block.end_time > existing_start:
                raise HTTPException(
                    status_code=409,
                    detail="O payload contém blocos sobrepostos no mesmo dia",
                )
        intervals.append((block.start_time, block.end_time))

    # Soft-delete all current active records
    result = await db.execute(
        select(StoreAvailability).where(
            StoreAvailability.professional_store_id == professional_store_id,
            StoreAvailability.deleted_at.is_(None),
        )
    )
    now = datetime.now(timezone.utc)
    for availability in result.scalars().all():
        availability.deleted_at = now

    # Create the new blocks
    new_records: list[StoreAvailability] = []
    for block in data.blocks:
        record = StoreAvailability(
            professional_store_id=professional_store_id,
            weekday=block.weekday,
            start_time=block.start_time,
            end_time=block.end_time,
        )
        db.add(record)
        new_records.append(record)

    await db.commit()
    for record in new_records:
        await db.refresh(record)
    return new_records
