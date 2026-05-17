from datetime import time

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.professional import Professional
from app.models.professional_store import ProfessionalStore
from app.models.store import Store
from app.models.user import User
from app.models.work_schedule import WorkSchedule
from app.schemas.work_schedule import WorkScheduleCreate, WorkScheduleUpdate
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
    """Raises 409 if [start_time, end_time) overlaps any active block on the same day."""
    q = select(WorkSchedule).where(
        WorkSchedule.professional_store_id == professional_store_id,
        WorkSchedule.weekday == weekday,
        WorkSchedule.is_active.is_(True),
        WorkSchedule.start_time < end_time,
        WorkSchedule.end_time > start_time,
    )
    if exclude_id is not None:
        q = q.where(WorkSchedule.id != exclude_id)
    result = await db.execute(q)
    if result.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=409,
            detail="O bloco de horário se sobrepõe a um existente neste dia",
        )


async def create_work_schedule(
    db: AsyncSession,
    professional_store_id: str,
    data: WorkScheduleCreate,
    user: User,
) -> WorkSchedule:
    await _verify_owner(db, professional_store_id, user)
    await _assert_no_overlap(
        db, professional_store_id, data.weekday, data.start_time, data.end_time
    )

    schedule = WorkSchedule(
        professional_store_id=professional_store_id,
        weekday=data.weekday,
        start_time=data.start_time,
        end_time=data.end_time,
    )
    db.add(schedule)
    await db.commit()
    await db.refresh(schedule)
    return schedule


async def list_professional_store_work_schedules(
    db: AsyncSession, professional_store_id: str
) -> list[WorkSchedule]:
    await get_professional_store(db, professional_store_id)
    result = await db.execute(
        select(WorkSchedule).where(
            WorkSchedule.professional_store_id == professional_store_id,
            WorkSchedule.is_active.is_(True),
        ).order_by(WorkSchedule.weekday)
    )
    return list(result.scalars().all())


async def get_work_schedule(db: AsyncSession, schedule_id: str) -> WorkSchedule:
    result = await db.execute(
        select(WorkSchedule).where(
            WorkSchedule.id == schedule_id,
            WorkSchedule.is_active.is_(True),
        )
    )
    schedule = result.scalar_one_or_none()
    if schedule is None:
        raise HTTPException(status_code=404, detail="Horário não encontrado")
    return schedule


async def update_work_schedule(
    db: AsyncSession,
    schedule_id: str,
    data: WorkScheduleUpdate,
    user: User,
) -> WorkSchedule:
    schedule = await get_work_schedule(db, schedule_id)
    await _verify_owner(db, schedule.professional_store_id, user)

    updates = data.model_dump(exclude_unset=True)
    if "start_time" in updates or "end_time" in updates:
        new_start = updates.get("start_time", schedule.start_time)
        new_end = updates.get("end_time", schedule.end_time)
        await _assert_no_overlap(
            db,
            schedule.professional_store_id,
            schedule.weekday,
            new_start,
            new_end,
            exclude_id=schedule_id,
        )

    for field, value in updates.items():
        setattr(schedule, field, value)

    await db.commit()
    await db.refresh(schedule)
    return schedule


async def delete_work_schedule(
    db: AsyncSession, schedule_id: str, user: User
) -> None:
    schedule = await get_work_schedule(db, schedule_id)
    await _verify_owner(db, schedule.professional_store_id, user)

    schedule.is_active = False
    await db.commit()
