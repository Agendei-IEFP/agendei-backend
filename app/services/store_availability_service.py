from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.store_availability import StoreAvailability
from app.models.user import User
from app.schemas.store_availability import StoreAvailabilityBulkReplace
from app.services.schedule_helper import verify_schedule_owner, validate_time_overlaps

async def replace_store_availability(
    db: AsyncSession, professional_store_id: str, data: StoreAvailabilityBulkReplace, user: User
) -> list[StoreAvailability]:
    await verify_schedule_owner(db, professional_store_id, user)
    validate_time_overlaps(data.blocks)

    # Soft-delete os registos ativos atuais
    result = await db.execute(
        select(StoreAvailability).where(
            StoreAvailability.professional_store_id == professional_store_id,
            StoreAvailability.deleted_at.is_(None)
        )
    )
    now = datetime.now(timezone.utc)
    for availability in result.scalars().all():
        availability.deleted_at = now

    # Criação em massa dos novos blocos
    new_records = [
        StoreAvailability(
            professional_store_id=professional_store_id,
            weekday=b.weekday,
            start_time=b.start_time,
            end_time=b.end_time
        ) for b in data.blocks
    ]
    db.add_all(new_records)
    await db.commit()
    return new_records