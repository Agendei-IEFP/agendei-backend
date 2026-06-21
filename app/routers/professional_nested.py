from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, require_role
from app.db.session import get_db
from app.models.user import RoleEnum, User
from app.schemas.appointment import AppointmentPublic, AvailableSlot
from app.schemas.work_schedule import WorkScheduleBulkUpsert, WorkSchedulePublic
from app.services import appointment_service, work_schedule_service

professionals_router = APIRouter(
    prefix="/professionals/{professional_id}",
    tags=["professionals"],
)

schedules_router = APIRouter(
    prefix="/professionals/{professional_id}/schedules",
    tags=["schedules"],
)


@professionals_router.get("/appointments", response_model=list[AppointmentPublic])
async def list_professional_appointments(
        professional_id: str,
        db: AsyncSession = Depends(get_db),
        user: User = Depends(get_current_user),
):
    return await appointment_service.list_professional_appointments(db, professional_id, user)


@professionals_router.get("/available-slots", response_model=list[AvailableSlot])
async def list_available_slots(
        professional_id: str,
        service_id: str = Query(..., description="Service ID"),
        on_date: date = Query(..., alias="date", description="Date in YYYY-MM-DD format"),
        db: AsyncSession = Depends(get_db),
):
    return await appointment_service.list_available_slots(
        db, professional_id, service_id, on_date
    )


@schedules_router.get("", response_model=list[WorkSchedulePublic])
async def list_work_schedules(professional_id: str, db: AsyncSession = Depends(get_db)):
    return await work_schedule_service.list_work_schedules(db, professional_id)


@schedules_router.put("", response_model=list[WorkSchedulePublic])
async def replace_work_schedules(
        professional_id: str,
        data: WorkScheduleBulkUpsert,
        db: AsyncSession = Depends(get_db),
        user: User = Depends(require_role(RoleEnum.professional, RoleEnum.store_admin)),
):
    return await work_schedule_service.replace_schedules(db, professional_id, data, user)
