from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, require_role
from app.db.session import get_db
from app.models.user import RoleEnum, User
from app.schemas.appointment import AppointmentPublic
from app.schemas.professional import ProfessionalPublic, ProfessionalStorePublic, ProfessionalUpdate, ProfessionalWithStorePublic
from app.schemas.store import StorePublic
from app.schemas.user import UserPublic
from app.services import appointment_service, professional_service, store_service

router = APIRouter(prefix="/me", tags=["me"])


@router.get("/user", response_model=UserPublic)
async def get_my_user(
    current_user: User = Depends(get_current_user),
):
    return current_user


@router.get("/stores", response_model=list[StorePublic])
async def list_my_stores(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(RoleEnum.store_admin)),
):
    return await store_service.list_my_stores(db, current_user.id)


@router.get("/appointments", response_model=list[AppointmentPublic])
async def list_my_appointments(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await appointment_service.list_client_appointments(db, current_user)


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
