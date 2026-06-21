from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.professional import Professional
from app.models.store import Store
from app.models.user import User
from app.models.work_schedule import WorkSchedule
from app.schemas.work_schedule import WorkScheduleBulkUpsert
from app.services.professional_service import get_professional


async def _verify_owner(db: AsyncSession, professional_id: str, user: User) -> Professional:
    professional = await get_professional(db, professional_id)
    store = await db.get(Store, professional.store_id)

    is_own = professional.user_id == user.id
    is_admin = store is not None and store.owner_id == user.id

    if not (is_own or is_admin):
        raise HTTPException(status_code=403, detail="Acesso negado")
    return professional


async def list_work_schedules(
    db: AsyncSession, professional_id: str
) -> list[WorkSchedule]:
    await get_professional(db, professional_id)
    result = await db.execute(
        select(WorkSchedule)
        .where(WorkSchedule.professional_id == professional_id)
        .order_by(WorkSchedule.weekday)
    )
    return list(result.scalars().all())


async def replace_schedules(
    db: AsyncSession,
    professional_id: str,
    data: WorkScheduleBulkUpsert,
    user: User,
) -> list[WorkSchedule]:
    await _verify_owner(db, professional_id, user)

    result = await db.execute(
        select(WorkSchedule).where(WorkSchedule.professional_id == professional_id)
    )
    existing = {ws.weekday: ws for ws in result.scalars().all()}

    updated: list[WorkSchedule] = []
    for entry in data.schedules:
        if entry.weekday in existing:
            ws = existing[entry.weekday]
            ws.start_time = entry.start_time
            ws.end_time = entry.end_time
            ws.is_active = entry.is_active
        else:
            ws = WorkSchedule(
                professional_id=professional_id,
                weekday=entry.weekday,
                start_time=entry.start_time,
                end_time=entry.end_time,
                is_active=entry.is_active,
            )
            db.add(ws)
        updated.append(ws)

    await db.commit()
    for ws in updated:
        await db.refresh(ws)
    return updated
