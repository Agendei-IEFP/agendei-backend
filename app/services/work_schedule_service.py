from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.work_schedule import WorkSchedule
from app.models.user import User
from app.schemas.work_schedule import WorkScheduleBulkReplace
from app.services.schedule_helper import verify_schedule_owner, validate_time_overlaps

async def replace_work_schedule(
    db: AsyncSession, professional_store_id: str, data: WorkScheduleBulkReplace, user: User
) -> list[WorkSchedule]:
    await verify_schedule_owner(db, professional_store_id, user)
    validate_time_overlaps(data.blocks)

    # Inativa os blocos atuais mudando a flag is_active
    result = await db.execute(
        select(WorkSchedule).where(
            WorkSchedule.professional_store_id == professional_store_id,
            WorkSchedule.is_active.is_(True)
        )
    )
    for schedule in result.scalars().all():
        schedule.is_active = False

    # Criação em massa dos novos blocos
    new_schedules = [
        WorkSchedule(
            professional_store_id=professional_store_id,
            weekday=b.weekday,
            start_time=b.start_time,
            end_time=b.end_time
        ) for b in data.blocks
    ]
    db.add_all(new_schedules)
    await db.commit()
    return new_schedules