from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.offering import Offering
from app.models.professional_store import ProfessionalStore
from app.models.store import Store, StoreType
from app.models.user import User
from app.schemas.store import StoreCreate, StorePublic, StoreUpdate


async def list_stores(
    db: AsyncSession, store_type: StoreType | None = None
) -> list[StorePublic]:
    # Cria uma subquery para ser usada dentro do execute abaixo
    professional_count_sq = (
        select(func.count(ProfessionalStore.id))
        .where(
            ProfessionalStore.store_id == Store.id,
            ProfessionalStore.deleted_at.is_(None),
        )
        .correlate(Store) # É o comando usado para dizer "Esse STORE não pertence a essa query, mas sim do query pai usada abaixo no execute"
        .scalar_subquery() # Transforma o select numa subquery que retorna um único valor
    )
    # Cria uma subquery para ser usada dentro do execute abaixo
    service_count_sq = (
        select(func.count(Offering.id))
        .join(ProfessionalStore, Offering.professional_store_id == ProfessionalStore.id)
        .where(
            ProfessionalStore.store_id == Store.id,
            Offering.is_enabled.is_(True),
            Offering.deleted_at.is_(None),
            ProfessionalStore.deleted_at.is_(None),
        )
        .correlate(Store)
        .scalar_subquery()
    )

    filters = [
        Store.deleted_at.is_(None),
        Store.is_active.is_(True),
    ]
    if store_type is not None:
        filters.append(Store.store_type == store_type)

    result = await db.execute(
        select(
            Store,
            professional_count_sq.label("professional_count"),
            service_count_sq.label("service_count"),
        ).where(*filters)
    )

    # Alternativa mais curta — evita listar todos os campos manualmente:
    # return [
    #     StorePublic.model_validate(store).model_copy(
    #         update={"professional_count": prof_count, "service_count": svc_count}
    #     )
    #     for store, prof_count, svc_count in result.all()
    # ]
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
            is_active=store.is_active,
            store_type=store.store_type,
            created_at=store.created_at,
            updated_at=store.updated_at,
            professional_count=prof_count,
            service_count=svc_count,
        )
        for store, prof_count, svc_count in result.all()
    ]


async def list_my_stores(db: AsyncSession, owner_id: str) -> list[Store]:
    result = await db.execute(
        select(Store).where(
            Store.owner_id == owner_id,
            Store.deleted_at.is_(None),
            Store.is_active.is_(True),
        )
    )
    return result.scalars().all()


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
