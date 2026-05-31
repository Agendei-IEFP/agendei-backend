from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import require_role
from app.db.session import get_db
from app.models.user import RoleEnum, User
from app.schemas.professional import (
    ProfessionalPublic,
    ProfessionalSelfCreate,
    ProfessionalStorePublic,
    ProfessionalUpdate,
    ProfessionalWithNamePublic,
)
from app.services import professional_service

router = APIRouter(prefix="/stores/{store_id}/professionals", tags=["professionals"])

professional_links_router = APIRouter(
    prefix="/stores/{store_id}/professional-links", tags=["professionals"]
)


@router.post("/me", response_model=ProfessionalStorePublic, status_code=status.HTTP_201_CREATED)
async def add_admin_as_professional(
    store_id: str,
    data: ProfessionalSelfCreate,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_role(RoleEnum.store_admin)),
):
    return await professional_service.add_admin_as_professional(db, store_id, data, admin)


@router.get("", response_model=list[ProfessionalWithNamePublic])
async def list_store_professionals(store_id: str, db: AsyncSession = Depends(get_db)):
    return await professional_service.list_store_professionals_with_name(db, store_id)


@router.patch("/{professional_id}", response_model=ProfessionalPublic)
async def update_professional(
    store_id: str,
    professional_id: str,
    data: ProfessionalUpdate,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_role(RoleEnum.store_admin)),
):
    return await professional_service.update_professional(db, store_id, professional_id, data, admin)


@professional_links_router.delete("/{professional_store_id}", status_code=status.HTTP_204_NO_CONTENT)
async def unlink_professional(
    store_id: str,
    professional_store_id: str,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_role(RoleEnum.store_admin)),
):
    await professional_service.unlink_professional_from_store(db, professional_store_id, admin)
