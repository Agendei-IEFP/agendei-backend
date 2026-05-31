from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import require_role
from app.db.session import get_db
from app.models.user import RoleEnum, User
from app.schemas.service import ServiceCreate, ServicePublic, ServiceUpdate
from app.services import service_service

router = APIRouter(prefix="/services", tags=["services"])


@router.post("", response_model=ServicePublic, status_code=status.HTTP_201_CREATED)
async def create_service(
    data: ServiceCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role(RoleEnum.professional, RoleEnum.store_admin)),
):
    return await service_service.create_service(db, data, user)


@router.get("/me", response_model=list[ServicePublic])
async def list_my_services(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role(RoleEnum.professional, RoleEnum.store_admin)),
):
    return await service_service.list_my_services(db, user)


@router.patch("/{service_id}", response_model=ServicePublic)
async def update_service(
    service_id: str,
    data: ServiceUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role(RoleEnum.professional, RoleEnum.store_admin)),
):
    return await service_service.update_service(db, service_id, data, user)


@router.delete("/{service_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_service(
    service_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role(RoleEnum.professional, RoleEnum.store_admin)),
):
    await service_service.delete_service(db, service_id, user)
