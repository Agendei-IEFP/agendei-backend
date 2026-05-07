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


async def create_work_schedule(
    db: AsyncSession,
    professional_store_id: str,
    data: WorkScheduleCreate,
    user: User,
) -> WorkSchedule:
    await _verify_owner(db, professional_store_id, user)

    already_exists = await db.execute(
        select(WorkSchedule).where(
            WorkSchedule.professional_store_id == professional_store_id,
            WorkSchedule.weekday == data.weekday,
            WorkSchedule.is_active.is_(True),
        )
    )
    if already_exists.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=409,
            detail=f"Já existe um horário ativo para o dia {data.weekday} neste vínculo",
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

    for field, value in data.model_dump(exclude_unset=True).items():
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
