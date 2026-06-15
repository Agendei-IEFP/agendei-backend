from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, require_role
from app.db.session import get_db
from app.models.user import RoleEnum, User
from app.schemas.appointment import AppointmentClientPublic, AppointmentPublic, AppointmentProfessionalPublic
from app.schemas.professional import ProfessionalPublic, ProfessionalUpdate, ProfessionalWithStorePublic
from app.schemas.store import StorePublic
from app.schemas.user import PasswordChange, UserPublic, UserUpdate
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


@router.patch("/password", status_code=204)
async def change_my_password(
    data: PasswordChange,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await user_service.change_password(db, current_user, data)
    return Response(status_code=204)


@router.post("/anonymize", status_code=204)
async def anonymize_my_account(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await user_service.anonymize_user(db, current_user)
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


def _serialize_professional_appt(a) -> dict:
    return {
        "id": a.id,
        "client_id": a.client_id,
        "professional_id": a.professional_id,
        "service_id": a.service_id,
        "store_id": a.store_id,
        "starts_at": a.starts_at,
        "ends_at": a.ends_at,
        "status": a.status,
        "cancelled_by": a.cancelled_by,
        "cancellation_reason": a.cancellation_reason,
        "reminder_sent": a.reminder_sent,
        "client_name": a.client.name if a.client else None,
        "client_phone": a.client.phone if a.client else None,
        "client_email": a.client.email if a.client else None,
        "service_name": a.service.name if a.service else None,
        "duration_minutes": a.service.duration_minutes if a.service else None,
        "store_name": a.store.name if a.store else None,
    }


@router.get("/professional-store", response_model=ProfessionalWithStorePublic)
async def get_my_professional_store(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(RoleEnum.professional, RoleEnum.store_admin)),
):
    professionals = await professional_service.list_my_professional_stores(db, current_user)
    if not professionals:
        raise HTTPException(status_code=404, detail="Perfil de profissional não encontrado")
    p = professionals[0]
    return ProfessionalWithStorePublic(
        id=p.id,
        user_id=p.user_id,
        store_id=p.store_id,
        name=p.user.name,
        bio=p.bio,
        photo_url=p.photo_url,
        is_active=p.is_active,
        store_name=p.store.name,
        store=p.store,
    )


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
    professionals = await professional_service.list_my_professionals(db, current_user)
    return [
        ProfessionalWithStorePublic(
            id=p.id,
            user_id=p.user_id,
            store_id=p.store_id,
            name=p.user.name,
            bio=p.bio,
            photo_url=p.photo_url,
            is_active=p.is_active,
            store_name=p.store.name,
            store=p.store,
        )
        for p in professionals
    ]
