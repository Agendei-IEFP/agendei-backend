from datetime import datetime, date, timedelta, timezone, time

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.appointment import Appointment, StatusEnum
from app.models.professional import Professional
from app.models.professional_store import ProfessionalStore
from app.models.store import Store
from app.models.user import User
from app.models.work_schedule import WorkSchedule
from app.schemas.appointment import AppointmentCreate, AppointmentUpdate, AvailableSlot
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

    1. Fetch the WorkSchedule for that link and weekday. If absent, return [].
    2. Fetch all conflicting appointments for that PROFESSIONAL (across every
       store they work in) — a busy slot anywhere blocks it everywhere.
    3. From the shift start, walk in offering-duration steps, dropping slots
       that collide with existing appointments.

    Because we store ends_at on Appointment, the collision check is just:
        new_start < existing_end AND new_end > existing_start
    """
    link = await get_professional_store(db, professional_store_id)
    offering = await get_offering(db, offering_id)
    if offering.professional_store_id != professional_store_id:
        raise HTTPException(
            status_code=422,
            detail="Este serviço não pertence a este vínculo profissional-loja",
        )

    weekday = query_date.weekday()  # 0=Monday, 6=Sunday
    result_schedule = await db.execute(
        select(WorkSchedule).where(
            WorkSchedule.professional_store_id == professional_store_id,
            WorkSchedule.weekday == weekday,
            WorkSchedule.is_active.is_(True),
        )
    )
    schedule = result_schedule.scalar_one_or_none()
    if schedule is None:
        return []

    day_start = datetime.combine(query_date, time.min).replace(tzinfo=timezone.utc)
    day_end = datetime.combine(query_date, time.max).replace(tzinfo=timezone.utc)

    result_appointments = await db.execute(
        select(Appointment).where(
            Appointment.professional_id == link.professional_id,
            Appointment.starts_at >= day_start,
            Appointment.starts_at <= day_end,
            Appointment.status.in_([StatusEnum.pending, StatusEnum.confirmed]),
        )
    )
    booked = list(result_appointments.scalars().all())

    duration = timedelta(minutes=offering.duration_minutes)
    slots: list[AvailableSlot] = []
    cursor = datetime.combine(query_date, schedule.start_time).replace(tzinfo=timezone.utc)
    shift_end = datetime.combine(query_date, schedule.end_time).replace(tzinfo=timezone.utc)
    now = datetime.now(timezone.utc)

    while cursor + duration <= shift_end:
        slot_start = cursor
        slot_end = cursor + duration

        if slot_start > now and not _collides(slot_start, slot_end, booked):
            slots.append(AvailableSlot(start=slot_start, end=slot_end))

        cursor += duration

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

    ends_at = starts_at + timedelta(minutes=offering.duration_minutes)

    # Final conflict check across every store this professional works in.
    conflict = await db.execute(
        select(Appointment).where(
            Appointment.professional_id == link.professional_id,
            Appointment.status.in_([StatusEnum.pending, StatusEnum.confirmed]),
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
        status=StatusEnum.pending,
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
        select(Appointment).where(
            Appointment.professional_id == professional_id,
            Appointment.deleted_at.is_(None),
        ).order_by(Appointment.starts_at.desc())
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
      pending → confirmed  (professional or admin)
      pending → cancelled  (any of the three)
      confirmed → completed (professional or admin)
      confirmed → cancelled (any of the three)

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
        StatusEnum.pending: [StatusEnum.confirmed, StatusEnum.cancelled],
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
