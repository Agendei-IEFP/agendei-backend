from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.professional import Professional
from app.models.service import Service
from app.models.store import Store
from app.models.user import User
from app.schemas.store import StoreCreate, StorePublic, StoreServicePublic, StoreUpdate


async def list_stores(db: AsyncSession) -> list[StorePublic]:
    professional_count_sq = (
        select(func.count(Professional.id))
        .where(
            Professional.store_id == Store.id,
            Professional.deleted_at.is_(None),
        )
        .correlate(Store)
        .scalar_subquery()
    )
    service_count_sq = (
        select(func.count(Service.id))
        .join(Professional, Professional.id == Service.professional_id)
        .where(
            Professional.store_id == Store.id,
            Professional.deleted_at.is_(None),
            Service.deleted_at.is_(None),
            Service.is_active.is_(True),
        )
        .correlate(Store)
        .scalar_subquery()
    )

    result = await db.execute(
        select(
            Store,
            professional_count_sq.label("professional_count"),
            service_count_sq.label("service_count"),
        ).where(
            Store.deleted_at.is_(None),
            Store.is_active.is_(True),
        )
    )

    return [
        StorePublic(
            id=store.id,
            owner_id=store.owner_id,
            name=store.name,
            description=store.description,
            phone=store.phone,
            email=store.email,
            address=store.address,
            logo_url=store.logo_url,
            banner_url=store.banner_url,
            is_active=store.is_active,
            store_types=store.store_types or [],
            created_at=store.created_at,
            updated_at=store.updated_at,
            professional_count=prof_count,
            service_count=svc_count,
        )
        for store, prof_count, svc_count in result.all()
    ]


async def list_my_stores(db: AsyncSession, owner_id: str) -> list[StorePublic]:
    professional_count_sq = (
        select(func.count(Professional.id))
        .where(
            Professional.store_id == Store.id,
            Professional.deleted_at.is_(None),
        )
        .correlate(Store)
        .scalar_subquery()
    )
    service_count_sq = (
        select(func.count(Service.id))
        .join(Professional, Professional.id == Service.professional_id)
        .where(
            Professional.store_id == Store.id,
            Professional.deleted_at.is_(None),
            Service.deleted_at.is_(None),
            Service.is_active.is_(True),
        )
        .correlate(Store)
        .scalar_subquery()
    )

    result = await db.execute(
        select(
            Store,
            professional_count_sq.label("professional_count"),
            service_count_sq.label("service_count"),
        ).where(
            Store.owner_id == owner_id,
            Store.deleted_at.is_(None),
        )
    )

    return [
        StorePublic(
            id=store.id,
            owner_id=store.owner_id,
            name=store.name,
            description=store.description,
            phone=store.phone,
            email=store.email,
            address=store.address,
            logo_url=store.logo_url,
            banner_url=store.banner_url,
            is_active=store.is_active,
            store_types=store.store_types or [],
            created_at=store.created_at,
            updated_at=store.updated_at,
            professional_count=prof_count,
            service_count=svc_count,
        )
        for store, prof_count, svc_count in result.all()
    ]


async def get_store(db: AsyncSession, store_id: str) -> Store:
    result = await db.execute(
        select(Store).where(Store.id == store_id, Store.deleted_at.is_(None))
    )
    store = result.scalar_one_or_none()
    if store is None:
        raise HTTPException(status_code=404, detail="Loja não encontrada")
    return store


async def create_store(db: AsyncSession, data: StoreCreate, owner_id: str) -> Store:
    store = Store(**data.model_dump(), owner_id=owner_id)
    db.add(store)
    await db.commit()
    await db.refresh(store)
    return store


async def update_store(
        db: AsyncSession,
        store_id: str,
        data: StoreUpdate,
        current_user: User,
) -> Store:
    store = await get_store(db, store_id)
    if store.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Acesso negado")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(store, field, value)
    await db.commit()
    await db.refresh(store)
    return store


async def delete_store(
        db: AsyncSession,
        store_id: str,
        current_user: User,
) -> None:
    store = await get_store(db, store_id)
    if store.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Acesso negado")
    store.deleted_at = datetime.now(timezone.utc)
    await db.commit()


async def list_store_services(db: AsyncSession, store_id: str) -> list[StoreServicePublic]:
    await get_store(db, store_id)

    result = await db.execute(
        select(Professional)
        .options(
            selectinload(Professional.user),
        )
        .where(
            Professional.store_id == store_id,
            Professional.deleted_at.is_(None),
            Professional.is_active.is_(True),
        )
    )
    professionals = result.scalars().all()

    if not professionals:
        return []

    professional_ids = [p.id for p in professionals]
    prof_by_id = {p.id: p for p in professionals}

    svc_result = await db.execute(
        select(Service).where(
            Service.professional_id.in_(professional_ids),
            Service.deleted_at.is_(None),
            Service.is_active.is_(True),
        ).order_by(Service.name)
    )
    services = svc_result.scalars().all()

    return [
        StoreServicePublic(
            service_id=s.id,
            service_name=s.name,
            price=s.price,
            duration_minutes=s.duration_minutes,
            professional_id=s.professional_id,
            professional_name=prof_by_id[s.professional_id].user.name,
        )
        for s in services
    ]
