from datetime import datetime, date, timedelta, timezone, time

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.appointment import Appointment, StatusEnum
from app.models.professional import Professional
from app.models.store import Store
from app.models.user import User
from app.models.work_schedule import WorkSchedule
from app.schemas.appointment import (
    AppointmentAdminPublic,
    AppointmentClientPublic,
    AppointmentCreate,
    AppointmentUpdate,
    AvailableSlot,
)
from app.services.professional_service import get_professional
from app.services.service_service import get_service


async def list_available_slots(
        db: AsyncSession,
        professional_id: str,
        service_id: str,
        query_date: date,
) -> list[AvailableSlot]:
    """
    Returns all free slots for a professional on a given day.

    1. Fetch the active WorkSchedule block for that professional+weekday.
    2. Fetch confirmed appointments for that professional on the day.
    3. Walk a 10-minute grid; offer slots where the service fits without collision.
    """
    SLOT_GRID_MINUTES = 10

    professional = await get_professional(db, professional_id)
    service = await get_service(db, service_id)

    if service.professional_id != professional_id:
        raise HTTPException(
            status_code=422,
            detail="Este serviço não pertence a este profissional",
        )

    weekday = query_date.weekday()

    result_schedule = await db.execute(
        select(WorkSchedule).where(
            WorkSchedule.professional_id == professional_id,
            WorkSchedule.weekday == weekday,
            WorkSchedule.is_active.is_(True),
        )
    )
    block = result_schedule.scalar_one_or_none()

    if block is None:
        return []

    day_start = datetime.combine(query_date, time.min).replace(tzinfo=timezone.utc)
    day_end = datetime.combine(query_date, time.max).replace(tzinfo=timezone.utc)

    result_appointments = await db.execute(
        select(Appointment).where(
            Appointment.professional_id == professional_id,
            Appointment.starts_at >= day_start,
            Appointment.starts_at <= day_end,
            Appointment.status == StatusEnum.confirmed,
        )
    )
    booked = list(result_appointments.scalars().all())

    duration = timedelta(minutes=service.duration_minutes)
    grid_step = timedelta(minutes=SLOT_GRID_MINUTES)
    now = datetime.now(timezone.utc)
    slots: list[AvailableSlot] = []

    cursor = datetime.combine(query_date, block.start_time).astimezone(timezone.utc)
    block_end = datetime.combine(query_date, block.end_time).astimezone(timezone.utc)

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
    for appt in appointments:
        if start < appt.ends_at and end > appt.starts_at:
            return True
    return False


async def create_appointment(
        db: AsyncSession,
        data: AppointmentCreate,
        client: User,
) -> Appointment:
    professional = await get_professional(db, data.professional_id)
    service = await get_service(db, data.service_id)

    if service.professional_id != data.professional_id:
        raise HTTPException(
            status_code=422,
            detail="Este serviço não pertence ao profissional indicado",
        )

    starts_at = data.starts_at
    if starts_at.tzinfo is None:
        starts_at = starts_at.replace(tzinfo=timezone.utc)

    ends_at = starts_at + timedelta(minutes=service.duration_minutes)

    conflict = await db.execute(
        select(Appointment).where(
            Appointment.professional_id == data.professional_id,
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
        professional_id=data.professional_id,
        service_id=data.service_id,
        store_id=professional.store_id,
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
            selectinload(Appointment.service),
            selectinload(Appointment.store),
            selectinload(Appointment.professional).selectinload(Professional.user),
        )
        .order_by(Appointment.starts_at.desc())
    )
    appointments = list(result.scalars().all())

    return [
        AppointmentClientPublic(
            id=a.id,
            starts_at=a.starts_at,
            ends_at=a.ends_at,
            status=a.status,
            notes=a.notes,
            cancelled_by=a.cancelled_by,
            cancellation_reason=a.cancellation_reason,
            service_name=a.service.name if a.service else None,
            professional_name=a.professional.user.name if a.professional and a.professional.user else None,
            store_name=a.store.name if a.store else None,
            price=a.service.price if a.service else None,
            duration_minutes=a.service.duration_minutes if a.service else None,
        )
        for a in appointments
    ]


async def list_professional_appointments(
        db: AsyncSession,
        professional_id: str,
        user: User,
) -> list[Appointment]:
    professional = await get_professional(db, professional_id)

    is_own = professional.user_id == user.id
    is_admin = False
    if not is_own:
        store = await db.get(Store, professional.store_id)
        is_admin = store is not None and store.owner_id == user.id

    if not is_own and not is_admin:
        raise HTTPException(status_code=403, detail="Acesso negado")

    result = await db.execute(
        select(Appointment)
        .options(
            selectinload(Appointment.client),
            selectinload(Appointment.service),
            selectinload(Appointment.store),
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
    appt = await get_appointment(db, appointment_id)
    professional = await get_professional(db, appt.professional_id)

    is_client = appt.client_id == user.id
    is_professional = professional.user_id == user.id

    store = await db.get(Store, appt.store_id)
    is_admin = store is not None and store.owner_id == user.id

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
    store = await db.get(Store, store_id)
    if store is None or store.deleted_at is not None:
        raise HTTPException(status_code=404, detail="Loja não encontrada")
    if store.owner_id != admin_id:
        raise HTTPException(status_code=403, detail="Acesso negado")

    query = (
        select(Appointment)
        .where(
            Appointment.store_id == store_id,
            Appointment.deleted_at.is_(None),
        )
        .options(
            selectinload(Appointment.client),
            selectinload(Appointment.professional).selectinload(Professional.user),
            selectinload(Appointment.service),
            selectinload(Appointment.store),
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
            professional_name=a.professional.user.name if a.professional and a.professional.user else None,
            service_name=a.service.name if a.service else None,
            store_name=a.store.name if a.store else None,
            duration_minutes=int((a.ends_at - a.starts_at).total_seconds() / 60),
            price=a.service.price if a.service else None,
        )
        for a in appts
    ]
