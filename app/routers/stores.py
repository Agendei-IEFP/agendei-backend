from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import require_role
from app.db.session import get_db
from app.models.user import RoleEnum, User
from app.schemas.appointment import AppointmentAdminPublic
from app.schemas.store import StoreCreate, StoreServicePublic, StorePublic, StoreUpdate
from app.services import store_service
from app.services import appointment_service

router = APIRouter(prefix="/stores", tags=["stores"])


@router.get("", response_model=list[StorePublic])
async def list_stores(db: AsyncSession = Depends(get_db)):
    return await store_service.list_stores(db)


@router.get("/{store_id}", response_model=StorePublic)
async def get_store(store_id: str, db: AsyncSession = Depends(get_db)):
    return await store_service.get_store(db, store_id)


@router.get("/{store_id}/services", response_model=list[StoreServicePublic])
async def list_store_services(store_id: str, db: AsyncSession = Depends(get_db)):
    return await store_service.list_store_services(db, store_id)


@router.post("", response_model=StorePublic, status_code=201)
async def create_store(
    data: StoreCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(RoleEnum.store_admin)),
):
    return await store_service.create_store(db, data, current_user.id)


@router.patch("/{store_id}", response_model=StorePublic)
async def update_store(
    store_id: str,
    data: StoreUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(RoleEnum.store_admin)),
):
    return await store_service.update_store(db, store_id, data, current_user)


@router.delete("/{store_id}", status_code=204)
async def delete_store(
    store_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(RoleEnum.store_admin)),
):
    await store_service.delete_store(db, store_id, current_user)


@router.get("/{store_id}/appointments", response_model=list[AppointmentAdminPublic])
async def list_store_appointments(
    store_id: str,
    date: date | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(RoleEnum.store_admin)),
):
    return await appointment_service.list_store_appointments(db, store_id, current_user.id, date)
