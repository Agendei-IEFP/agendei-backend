from datetime import date

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, require_role
from app.db.session import get_db
from app.models.user import RoleEnum, User
from app.schemas.appointment import AppointmentPublic, AvailableSlot
from app.schemas.professional import (
    ProfessionalCreate,
    ProfessionalPublic,
    ProfessionalSelfCreate,
    ProfessionalUpdate,
    ProfessionalWithNamePublic,
)
from app.services import appointment_service, professional_service

store_professionals_router = APIRouter(
    prefix="/stores/{store_id}/professionals",
    tags=["professionals"],
)

professionals_router = APIRouter(
    prefix="/professionals/{professional_id}",
    tags=["professionals"],
)


# ---------------------------------------------------------------------------
# /stores/{store_id}/professionals
# ---------------------------------------------------------------------------


@store_professionals_router.post(
    "/me", response_model=ProfessionalPublic, status_code=status.HTTP_201_CREATED
)
async def add_admin_as_professional(
    store_id: str,
    data: ProfessionalSelfCreate,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_role(RoleEnum.store_admin)),
):
    return await professional_service.add_admin_as_professional(db, store_id, data, admin)


@store_professionals_router.post(
    "", response_model=ProfessionalWithNamePublic, status_code=status.HTTP_201_CREATED
)
async def create_professional(
    store_id: str,
    data: ProfessionalCreate,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_role(RoleEnum.store_admin)),
):
    return await professional_service.create_professional(db, store_id, data, admin)


@store_professionals_router.get("", response_model=list[ProfessionalWithNamePublic])
async def list_store_professionals(store_id: str, db: AsyncSession = Depends(get_db)):
    return await professional_service.list_store_professionals_with_name(db, store_id)


@store_professionals_router.patch(
    "/{professional_id}", response_model=ProfessionalPublic
)
async def update_professional(
    store_id: str,
    professional_id: str,
    data: ProfessionalUpdate,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_role(RoleEnum.store_admin)),
):
    return await professional_service.update_professional(
        db, store_id, professional_id, data, admin
    )


@store_professionals_router.delete(
    "/{professional_id}", status_code=status.HTTP_204_NO_CONTENT
)
async def unlink_professional(
    store_id: str,
    professional_id: str,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_role(RoleEnum.store_admin)),
):
    await professional_service.unlink_professional_from_store(
        db, professional_id, store_id, admin
    )


# ---------------------------------------------------------------------------
# /professionals/{professional_id}
# ---------------------------------------------------------------------------


@professionals_router.get("/appointments", response_model=list[AppointmentPublic])
async def list_professional_appointments(
    professional_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return await appointment_service.list_professional_appointments(
        db, professional_id, user
    )


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
