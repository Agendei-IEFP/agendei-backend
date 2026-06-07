from datetime import datetime, date, timedelta, timezone, time

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.appointment import Appointment, StatusEnum
from app.models.offering import Offering
from app.models.professional import Professional
from app.models.professional_store import ProfessionalStore
from app.models.store import Store
from app.models.store_availability import StoreAvailability
from app.models.user import User
from app.models.work_schedule import WorkSchedule
from app.schemas.appointment import AppointmentAdminPublic, AppointmentClientPublic, AppointmentCreate, AppointmentUpdate, AvailableSlot
from app.services.offering_service import get_offering
from app.services.professional_service import get_professional, get_professional_store


# ---------------------------------------------------------------------------
# Available slots algorithm
# ---------------------------------------------------------------------------

async def list_available_slots(
    db: AsyncSession,
    professional_store_id: str,
    offering_id: str,
    query_date: date,
) -> list[AvailableSlot]:
    """
    Returns all free slots for a (professional, store) link on a given day.

    1. Fetch all active WorkSchedule blocks for that link and weekday.
       If none, return [].
    2. Fetch all conflicting appointments for that PROFESSIONAL (across every
       store they work in) — a busy slot anywhere blocks it everywhere.
    3. For each block, walk a fixed 10-minute grid. A slot is offered only if
       the full service duration fits within the block (no crossing pauses)
       and doesn't collide with existing appointments.

    Because we store ends_at on Appointment, the collision check is:
        new_start < existing_end AND new_end > existing_start
    """
    SLOT_GRID_MINUTES = 10

    link = await get_professional_store(db, professional_store_id)
    offering = await get_offering(db, offering_id)
    if offering.professional_store_id != professional_store_id:
        raise HTTPException(
            status_code=422,
            detail="Este serviço não pertence a este vínculo profissional-loja",
        )

    weekday = query_date.weekday()  # 0=Monday, 6=Sunday

    # Use StoreAvailability overrides when present; fall back to base WorkSchedule
    result_overrides = await db.execute(
        select(StoreAvailability).where(
            StoreAvailability.professional_store_id == professional_store_id,
            StoreAvailability.weekday == weekday,
            StoreAvailability.deleted_at.is_(None),
            StoreAvailability.is_active.is_(True),
        ).order_by(StoreAvailability.start_time)
    )
    override_blocks = list(result_overrides.scalars().all())

    if override_blocks:
        blocks = override_blocks
    else:
        result_schedules = await db.execute(
            select(WorkSchedule).where(
                WorkSchedule.professional_store_id == professional_store_id,
                WorkSchedule.weekday == weekday,
                WorkSchedule.is_active.is_(True),
            ).order_by(WorkSchedule.start_time)
        )
        blocks = list(result_schedules.scalars().all())

    if not blocks:
        return []

    day_start = datetime.combine(query_date, time.min).replace(tzinfo=timezone.utc)
    day_end = datetime.combine(query_date, time.max).replace(tzinfo=timezone.utc)

    result_appointments = await db.execute(
        select(Appointment).where(
            Appointment.professional_id == link.professional_id,
            Appointment.starts_at >= day_start,
            Appointment.starts_at <= day_end,
            Appointment.status == StatusEnum.confirmed,
        )
    )
    booked = list(result_appointments.scalars().all())

    effective_duration = offering.duration_override if offering.duration_override is not None else offering.service.default_duration_minutes
    duration = timedelta(minutes=effective_duration)
    grid_step = timedelta(minutes=SLOT_GRID_MINUTES)
    now = datetime.now(timezone.utc)
    slots: list[AvailableSlot] = []

    for block in blocks:
        cursor = datetime.combine(query_date, block.start_time).replace(tzinfo=timezone.utc)
        block_end = datetime.combine(query_date, block.end_time).replace(tzinfo=timezone.utc)

        while cursor + duration <= block_end:
            slot_start = cursor
            slot_end = cursor + duration

            if slot_start > now and not _collides(slot_start, slot_end, booked):
                slots.append(AvailableSlot(start=slot_start, end=slot_end))

            cursor += grid_step

    return slots


def _collides(
    start: datetime,
    end: datetime,
    appointments: list[Appointment],
) -> bool:
    """
    Two intervals [A, B] and [C, D] overlap if: A < D AND B > C
    """
    for appt in appointments:
        if start < appt.ends_at and end > appt.starts_at:
            return True
    return False


# ---------------------------------------------------------------------------
# Appointment CRUD
# ---------------------------------------------------------------------------

async def create_appointment(
    db: AsyncSession,
    data: AppointmentCreate,
    client: User,
) -> Appointment:
    """
    Creates an appointment for the authenticated client.
    Validates:
      - The offering belongs to the indicated professional-store link
      - The slot is still free across all of that professional's stores
    Resolves Appointment.professional_id (denormalized) from the link.
    """
    link = await get_professional_store(db, data.professional_store_id)
    offering = await get_offering(db, data.offering_id)

    if offering.professional_store_id != data.professional_store_id:
        raise HTTPException(
            status_code=422,
            detail="Este serviço não pertence ao vínculo profissional-loja indicado",
        )

    starts_at = data.starts_at
    if starts_at.tzinfo is None:
        starts_at = starts_at.replace(tzinfo=timezone.utc)

    effective_duration = offering.duration_override if offering.duration_override is not None else offering.service.default_duration_minutes
    ends_at = starts_at + timedelta(minutes=effective_duration)

    # Final conflict check across every store this professional works in.
    conflict = await db.execute(
        select(Appointment).where(
            Appointment.professional_id == link.professional_id,
            Appointment.status == StatusEnum.confirmed,
            Appointment.starts_at < ends_at,
            Appointment.ends_at > starts_at,
        )
    )
    if conflict.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=409,
            detail="Este horário não está mais disponível",
        )

    appointment = Appointment(
        client_id=client.id,
        professional_id=link.professional_id,
        professional_store_id=link.id,
        offering_id=data.offering_id,
        starts_at=starts_at,
        ends_at=ends_at,
        status=StatusEnum.confirmed,
    )
    db.add(appointment)
    await db.commit()
    await db.refresh(appointment)
    return appointment


async def list_client_appointments(
    db: AsyncSession, client: User
) -> list[Appointment]:
    result = await db.execute(
        select(Appointment).where(
            Appointment.client_id == client.id,
            Appointment.deleted_at.is_(None),
        ).order_by(Appointment.starts_at.desc())
    )
    return list(result.scalars().all())


async def list_client_appointments_detailed(
    db: AsyncSession, client: User
) -> list[AppointmentClientPublic]:
    result = await db.execute(
        select(Appointment)
        .where(
            Appointment.client_id == client.id,
            Appointment.deleted_at.is_(None),
        )
        .options(
            selectinload(Appointment.offering).selectinload(Offering.service),
            selectinload(Appointment.professional_store).selectinload(ProfessionalStore.store),
            selectinload(Appointment.professional).selectinload(Professional.user),
        )
        .order_by(Appointment.starts_at.desc())
    )
    appointments = list(result.scalars().all())

    items = []
    for apt in appointments:
        offering = apt.offering
        service = offering.service if offering else None
        prof_store = apt.professional_store
        store = prof_store.store if prof_store else None
        professional = apt.professional

        items.append(AppointmentClientPublic(
            id=apt.id,
            starts_at=apt.starts_at,
            ends_at=apt.ends_at,
            status=apt.status,
            notes=apt.notes,
            cancelled_by=apt.cancelled_by,
            cancellation_reason=apt.cancellation_reason,
            service_name=service.name if service else None,
            professional_name=professional.user.name if professional and professional.user else None,
            store_name=store.name if store else None,
            effective_price=offering.price_override if offering and offering.price_override is not None else (service.default_price if service else None),
            effective_duration_minutes=offering.duration_override if offering and offering.duration_override is not None else (service.default_duration_minutes if service else None),
        ))
    return items


async def list_professional_appointments(
    db: AsyncSession,
    professional_id: str,
    user: User,
) -> list[Appointment]:
    """
    Unified view of every appointment for this professional, across all stores.
    Allowed: the professional themselves, or the admin of ANY store they're
    currently linked to.
    """
    professional = await get_professional(db, professional_id)

    is_own = professional.user_id == user.id
    is_admin_of_any_linked_store = False
    if not is_own:
        result = await db.execute(
            select(Store.id)
            .join(ProfessionalStore, ProfessionalStore.store_id == Store.id)
            .where(
                ProfessionalStore.professional_id == professional_id,
                ProfessionalStore.deleted_at.is_(None),
                Store.deleted_at.is_(None),
                Store.owner_id == user.id,
            )
            .limit(1)
        )
        is_admin_of_any_linked_store = result.scalar_one_or_none() is not None

    if not is_own and not is_admin_of_any_linked_store:
        raise HTTPException(status_code=403, detail="Acesso negado")

    result = await db.execute(
        select(Appointment)
        .options(
            selectinload(Appointment.client),
            selectinload(Appointment.offering).selectinload(Offering.service),
            selectinload(Appointment.professional_store).selectinload(ProfessionalStore.store),
        )
        .where(
            Appointment.professional_id == professional_id,
            Appointment.deleted_at.is_(None),
        )
        .order_by(Appointment.starts_at.asc())
    )
    return list(result.scalars().all())


async def get_appointment(db: AsyncSession, appointment_id: str) -> Appointment:
    result = await db.execute(
        select(Appointment).where(
            Appointment.id == appointment_id,
            Appointment.deleted_at.is_(None),
        )
    )
    appt = result.scalar_one_or_none()
    if appt is None:
        raise HTTPException(status_code=404, detail="Agendamento não encontrado")
    return appt


async def update_status(
    db: AsyncSession,
    appointment_id: str,
    data: AppointmentUpdate,
    user: User,
) -> Appointment:
    """
    Valid transitions:
      confirmed → completed (professional or admin)
      confirmed → cancelled (professional, admin, or client)

    Records who cancelled for audit purposes.
    """
    appt = await get_appointment(db, appointment_id)
    professional = await get_professional(db, appt.professional_id)

    is_client = appt.client_id == user.id
    is_professional = professional.user_id == user.id

    # Admin = owner of the store of the link this appointment is on.
    link = await get_professional_store(db, appt.professional_store_id)
    from app.services.store_service import get_store
    store = await get_store(db, link.store_id)
    is_admin = store.owner_id == user.id

    if not (is_client or is_professional or is_admin):
        raise HTTPException(status_code=403, detail="Acesso negado")

    VALID_TRANSITIONS = {
        StatusEnum.confirmed: [StatusEnum.completed, StatusEnum.cancelled],
        StatusEnum.completed: [],
        StatusEnum.cancelled: [],
    }
    if data.status not in VALID_TRANSITIONS[appt.status]:
        raise HTTPException(
            status_code=422,
            detail=f"Não é possível mover de '{appt.status}' para '{data.status}'",
        )

    if is_client and not (is_professional or is_admin):
        if data.status != StatusEnum.cancelled:
            raise HTTPException(
                status_code=403,
                detail="Clientes só podem cancelar agendamentos",
            )

    if data.status == StatusEnum.completed:
        now = datetime.now(timezone.utc)
        if appt.starts_at > now:
            raise HTTPException(
                status_code=422,
                detail="Só é possível concluir um agendamento após a data/hora de início",
            )

    appt.status = data.status
    if data.status == StatusEnum.cancelled:
        appt.cancelled_by = user.id
        appt.cancellation_reason = data.reason

    await db.commit()
    await db.refresh(appt)
    return appt


async def list_store_appointments(
    db: AsyncSession,
    store_id: str,
    admin_id: str,
    date_filter: date | None = None,
) -> list[AppointmentAdminPublic]:
    result = await db.execute(
        select(Store).where(Store.id == store_id, Store.deleted_at.is_(None))
    )
    store = result.scalar_one_or_none()
    if store is None:
        raise HTTPException(status_code=404, detail="Loja não encontrada")
    if store.owner_id != admin_id:
        raise HTTPException(status_code=403, detail="Acesso negado")

    query = (
        select(Appointment)
        .join(ProfessionalStore, ProfessionalStore.id == Appointment.professional_store_id)
        .where(
            ProfessionalStore.store_id == store_id,
            Appointment.deleted_at.is_(None),
        )
        .options(
            selectinload(Appointment.client),
            selectinload(Appointment.professional).selectinload(Professional.user),
            selectinload(Appointment.professional_store).selectinload(ProfessionalStore.store),
            selectinload(Appointment.offering).selectinload(Offering.service),
        )
        .order_by(Appointment.starts_at.asc())
    )

    if date_filter is not None:
        day_start = datetime.combine(date_filter, time.min).replace(tzinfo=timezone.utc)
        day_end = datetime.combine(date_filter, time.max).replace(tzinfo=timezone.utc)
        query = query.where(Appointment.starts_at >= day_start, Appointment.starts_at <= day_end)

    result = await db.execute(query)
    appts = list(result.scalars().all())

    return [
        AppointmentAdminPublic(
            id=a.id,
            starts_at=a.starts_at,
            ends_at=a.ends_at,
            status=a.status,
            client_name=a.client.name if a.client else None,
            professional_name=(
                a.professional.user.name
                if a.professional and a.professional.user
                else None
            ),
            service_name=(
                a.offering.service.name
                if a.offering and a.offering.service
                else None
            ),
            store_name=(
                a.professional_store.store.name
                if a.professional_store and a.professional_store.store
                else None
            ),
            duration_minutes=int((a.ends_at - a.starts_at).total_seconds() / 60),
            effective_price=(
                a.offering.price_override
                if a.offering and a.offering.price_override is not None
                else (a.offering.service.default_price if a.offering and a.offering.service else None)
            ),
        )
        for a in appts
    ]
