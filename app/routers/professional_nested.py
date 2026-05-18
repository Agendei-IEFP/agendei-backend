from datetime import date

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, require_role
from app.db.session import get_db
from app.models.user import RoleEnum, User
from app.schemas.appointment import AppointmentPublic, AvailableSlot
from app.schemas.offering import OfferingCreate, OfferingPublic, OfferingUpdate
from app.schemas.store_availability import (
    StoreAvailabilityBulkReplace,
    StoreAvailabilityCreate,
    StoreAvailabilityPublic,
    StoreAvailabilityUpdate,
)
from app.schemas.work_schedule import WorkScheduleBulkReplace, WorkScheduleCreate, WorkSchedulePublic, WorkScheduleUpdate
from app.services import appointment_service, offering_service, store_availability_service, work_schedule_service

professionals_router = APIRouter(
    prefix="/professionals/{professional_id}",
    tags=["professionals"],
)

prof_store_router = APIRouter(
    prefix="/professional-stores/{professional_store_id}",
    tags=["professional-stores"],
)

offerings_router = APIRouter(
    prefix="/professional-stores/{professional_store_id}/offerings",
    tags=["offerings"],
)

schedules_router = APIRouter(
    prefix="/professional-stores/{professional_store_id}/schedules",
    tags=["schedules"],
)

availability_router = APIRouter(
    prefix="/professional-stores/{professional_store_id}/availability",
    tags=["availability"],
)


# ---------------------------------------------------------------------------
# Professional-level (cross-store)
# ---------------------------------------------------------------------------


@professionals_router.get("/appointments", response_model=list[AppointmentPublic])
async def list_professional_appointments(
    professional_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return await appointment_service.list_professional_appointments(db, professional_id, user)


# ---------------------------------------------------------------------------
# Professional-store-level
# ---------------------------------------------------------------------------


@prof_store_router.get("/available-slots", response_model=list[AvailableSlot])
async def list_available_slots(
    professional_store_id: str,
    offering_id: str = Query(..., description="Offering ID"),
    on_date: date = Query(..., alias="date", description="Date in YYYY-MM-DD format"),
    db: AsyncSession = Depends(get_db),
):
    return await appointment_service.list_available_slots(
        db, professional_store_id, offering_id, on_date
    )


# ---------------------------------------------------------------------------
# Offerings
# ---------------------------------------------------------------------------


@offerings_router.post("", response_model=OfferingPublic, status_code=status.HTTP_201_CREATED)
async def create_offering(
    professional_store_id: str,
    data: OfferingCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role(RoleEnum.professional, RoleEnum.store_admin)),
):
    return await offering_service.create_offering(db, professional_store_id, data, user)


@offerings_router.get("", response_model=list[OfferingPublic])
async def list_offerings(professional_store_id: str, db: AsyncSession = Depends(get_db)):
    return await offering_service.list_professional_store_offerings(db, professional_store_id)


@offerings_router.patch("/{offering_id}", response_model=OfferingPublic)
async def update_offering(
    professional_store_id: str,
    offering_id: str,
    data: OfferingUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role(RoleEnum.professional, RoleEnum.store_admin)),
):
    return await offering_service.update_offering(db, offering_id, data, user)


@offerings_router.delete("/{offering_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_offering(
    professional_store_id: str,
    offering_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role(RoleEnum.professional, RoleEnum.store_admin)),
):
    await offering_service.delete_offering(db, offering_id, user)


# ---------------------------------------------------------------------------
# Work schedules
# ---------------------------------------------------------------------------


@schedules_router.post("", response_model=WorkSchedulePublic, status_code=status.HTTP_201_CREATED)
async def create_work_schedule(
    professional_store_id: str,
    data: WorkScheduleCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role(RoleEnum.professional, RoleEnum.store_admin)),
):
    return await work_schedule_service.create_work_schedule(
        db, professional_store_id, data, user
    )


@schedules_router.get("", response_model=list[WorkSchedulePublic])
async def list_work_schedules(professional_store_id: str, db: AsyncSession = Depends(get_db)):
    return await work_schedule_service.list_professional_store_work_schedules(
        db, professional_store_id
    )


@schedules_router.patch("/{schedule_id}", response_model=WorkSchedulePublic)
async def update_work_schedule(
    professional_store_id: str,
    schedule_id: str,
    data: WorkScheduleUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role(RoleEnum.professional, RoleEnum.store_admin)),
):
    return await work_schedule_service.update_work_schedule(db, schedule_id, data, user)


@schedules_router.delete("/{schedule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_work_schedule(
    professional_store_id: str,
    schedule_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role(RoleEnum.professional, RoleEnum.store_admin)),
):
    await work_schedule_service.delete_work_schedule(db, schedule_id, user)


@schedules_router.put("", response_model=list[WorkSchedulePublic])
async def replace_work_schedules(
    professional_store_id: str,
    data: WorkScheduleBulkReplace,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role(RoleEnum.professional, RoleEnum.store_admin)),
):
    return await work_schedule_service.replace_blocks(db, professional_store_id, data, user)


# ---------------------------------------------------------------------------
# Store availability overrides
# ---------------------------------------------------------------------------


@availability_router.get("", response_model=list[StoreAvailabilityPublic])
async def list_store_availability(
    professional_store_id: str, db: AsyncSession = Depends(get_db)
):
    return await store_availability_service.list_store_availability(db, professional_store_id)


@availability_router.post(
    "", response_model=StoreAvailabilityPublic, status_code=status.HTTP_201_CREATED
)
async def create_store_availability(
    professional_store_id: str,
    data: StoreAvailabilityCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role(RoleEnum.professional, RoleEnum.store_admin)),
):
    return await store_availability_service.create_store_availability(
        db, professional_store_id, data, user
    )


@availability_router.patch("/{availability_id}", response_model=StoreAvailabilityPublic)
async def update_store_availability(
    professional_store_id: str,
    availability_id: str,
    data: StoreAvailabilityUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role(RoleEnum.professional, RoleEnum.store_admin)),
):
    return await store_availability_service.update_store_availability(
        db, availability_id, data, user
    )


@availability_router.delete("/{availability_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_store_availability(
    professional_store_id: str,
    availability_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role(RoleEnum.professional, RoleEnum.store_admin)),
):
    await store_availability_service.delete_store_availability(db, availability_id, user)


@availability_router.put("", response_model=list[StoreAvailabilityPublic])
async def replace_store_availability(
    professional_store_id: str,
    data: StoreAvailabilityBulkReplace,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role(RoleEnum.professional, RoleEnum.store_admin)),
):
    return await store_availability_service.replace_availability(db, professional_store_id, data, user)
