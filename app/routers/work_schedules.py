from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import require_role
from app.db.session import get_db
from app.models.user import RoleEnum, User
from app.schemas.work_schedule import WorkScheduleBulkUpsert, WorkSchedulePublic
from app.services import work_schedule_service

router = APIRouter(
    prefix="/professionals/{professional_id}/schedules",
    tags=["schedules"],
)


@router.get("", response_model=list[WorkSchedulePublic])
async def list_work_schedules(professional_id: str, db: AsyncSession = Depends(get_db)):
    return await work_schedule_service.list_work_schedules(db, professional_id)


@router.put("", response_model=list[WorkSchedulePublic])
async def replace_work_schedules(
    professional_id: str,
    data: WorkScheduleBulkUpsert,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role(RoleEnum.professional, RoleEnum.store_admin)),
):
    return await work_schedule_service.replace_schedules(db, professional_id, data, user)
