from datetime import time
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.professional import Professional
from app.models.professional_store import ProfessionalStore
from app.models.store import Store
from app.models.user import User


async def verify_schedule_owner(db: AsyncSession, professional_store_id: str, user: User) -> ProfessionalStore:
    """Verifica se o utilizador é o profissional ou o dono da loja do vínculo."""
    result = await db.execute(
        select(ProfessionalStore, Professional, Store)
        .join(Professional, Professional.id == ProfessionalStore.professional_id)
        .join(Store, Store.id == ProfessionalStore.store_id)
        .where(ProfessionalStore.id == professional_store_id, ProfessionalStore.deleted_at.is_(None))
    )
    row = result.first()
    if not row:
        raise HTTPException(status_code=404, detail="Vínculo profissional-loja não encontrado")

    link, professional, store = row
    if professional.user_id != user.id and store.owner_id != user.id:
        raise HTTPException(status_code=403, detail="Acesso negado")
    return link


def validate_time_overlaps(blocks: list) -> None:
    """Valida se existem blocos de horários sobrepostos no mesmo dia dentro do payload."""
    seen: dict[int, list[tuple[time, time]]] = {}
    for block in blocks:
        intervals = seen.setdefault(block.weekday, [])
        for ex_start, ex_end in intervals:
            if block.start_time < ex_end and block.end_time > ex_start:
                raise HTTPException(
                    status_code=409,
                    detail="O payload contém blocos sobrepostos no mesmo dia"
                )
        intervals.append((block.start_time, block.end_time))