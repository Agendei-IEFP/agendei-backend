from fastapi import APIRouter, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, require_role
from app.db.session import get_db
from app.models.user import RoleEnum, User
from app.schemas.appointment import AppointmentClientPublic, AppointmentPublic, AppointmentProfessionalPublic
from app.schemas.professional import ProfessionalPublic, ProfessionalStorePublic, ProfessionalUpdate, ProfessionalWithStorePublic
from app.schemas.store import StorePublic
from app.schemas.user import UserPublic, UserUpdate
from app.services import appointment_service, professional_service, store_service, user_service

router = APIRouter(prefix="/me", tags=["me"])


@router.get("/user", response_model=UserPublic)
async def get_my_user(
    current_user: User = Depends(get_current_user),
):
    return current_user


@router.patch("/user", response_model=UserPublic)
async def update_my_user(
    data: UserUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await user_service.update_user(db, current_user, data)


@router.delete("/user", status_code=204)
async def delete_my_user(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await user_service.delete_user(db, current_user)
    return Response(status_code=204)


@router.get("/stores", response_model=list[StorePublic])
async def list_my_stores(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(RoleEnum.store_admin)),
):
    return await store_service.list_my_stores(db, current_user.id)


@router.get("/appointments", response_model=list[AppointmentClientPublic])
async def list_my_appointments(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await appointment_service.list_client_appointments_detailed(db, current_user)


@router.get("/professional-appointments", response_model=list[AppointmentProfessionalPublic])
async def list_my_professional_appointments(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(RoleEnum.professional)),
):
    professional = await professional_service.get_my_profile(db, current_user)
    appointments = await appointment_service.list_professional_appointments(
        db, professional.id, current_user
    )
    return [_serialize_professional_appt(a) for a in appointments]


def _serialize_professional_appt(a):
    offering = a.offering
    service = offering.service if offering else None
    return {
        "id": a.id,
        "client_id": a.client_id,
        "professional_id": a.professional_id,
        "professional_store_id": a.professional_store_id,
        "offering_id": a.offering_id,
        "starts_at": a.starts_at,
        "ends_at": a.ends_at,
        "status": a.status,
        "cancelled_by": a.cancelled_by,
        "cancellation_reason": a.cancellation_reason,
        "reminder_sent": a.reminder_sent,
        "client_name": a.client.name if a.client else None,
        "service_name": service.name if service else None,
        "duration_minutes": (
            offering.duration_override
            if offering and offering.duration_override is not None
            else (service.default_duration_minutes if service else None)
        ),
        "store_name": a.professional_store.store.name if a.professional_store and a.professional_store.store else None,
    }


@router.get("/professional-stores", response_model=list[ProfessionalStorePublic])
async def list_my_professional_stores(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await professional_service.list_user_professional_stores(db, current_user)


@router.get("/professional", response_model=ProfessionalPublic)
async def get_my_professional_profile(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await professional_service.get_my_profile(db, current_user)


@router.patch("/professional", response_model=ProfessionalPublic)
async def update_my_professional_profile(
    data: ProfessionalUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(RoleEnum.professional, RoleEnum.store_admin)),
):
    return await professional_service.update_my_profile(db, data, current_user)


@router.get("/professionals", response_model=list[ProfessionalWithStorePublic])
async def list_my_professionals(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(RoleEnum.store_admin)),
):
    rows = await professional_service.list_my_professionals(db, current_user)
    return [ProfessionalWithStorePublic.model_validate(row) for row in rows]
