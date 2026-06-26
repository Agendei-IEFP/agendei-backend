from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, require_role
from app.db.session import get_db
from app.models.user import RoleEnum, User
from app.schemas.appointment import AppointmentClientPublic, AppointmentProfessionalPublic
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
    return [AppointmentProfessionalPublic.model_validate(a) for a in appointments]


@router.get("/professional-store", response_model=ProfessionalWithStorePublic)
async def get_my_professional_store(
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(require_role(RoleEnum.professional, RoleEnum.store_admin)),
):
    professional = await professional_service.get_my_store_professional(db, current_user)
    return ProfessionalWithStorePublic.model_validate(professional)


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
    return [ProfessionalWithStorePublic.model_validate(p) for p in professionals]
