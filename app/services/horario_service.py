from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException

from app.models.horario_trabalho import HorarioTrabalho
from app.models.usuario import Usuario
from app.schemas.horario_trabalho import HorarioTrabalhoCreate, HorarioTrabalhoUpdate
from app.services.profissional_service import buscar_profissional
from app.services.loja_service import buscar_loja


async def _verificar_dono(db: AsyncSession, profissional_id: str, admin: Usuario) -> None:
    profissional = await buscar_profissional(db, profissional_id)
    loja = await buscar_loja(db, profissional.loja_id)
    if loja.owner_id != admin.id:
        raise HTTPException(status_code=403, detail="Acesso negado")


async def criar_horario(
    db: AsyncSession,
    profissional_id: str,
    data: HorarioTrabalhoCreate,
    admin: Usuario,
) -> HorarioTrabalho:
    await _verificar_dono(db, profissional_id, admin)

    # Um profissional só pode ter um horário ativo por dia da semana
    ja_existe = await db.execute(
        select(HorarioTrabalho).where(
            HorarioTrabalho.profissional_id == profissional_id,
            HorarioTrabalho.dia_semana == data.dia_semana,
            HorarioTrabalho.is_active.is_(True),
        )
    )
    if ja_existe.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=409,
            detail=f"Já existe um horário ativo para o dia {data.dia_semana} neste profissional",
        )

    horario = HorarioTrabalho(
        profissional_id=profissional_id,
        dia_semana=data.dia_semana,
        hora_inicio=data.hora_inicio,
        hora_fim=data.hora_fim,
    )
    db.add(horario)
    await db.commit()
    await db.refresh(horario)
    return horario


async def listar_horarios_do_profissional(
    db: AsyncSession, profissional_id: str
) -> list[HorarioTrabalho]:
    """Rota pública — clientes precisam saber quando o profissional trabalha."""
    await buscar_profissional(db, profissional_id)
    result = await db.execute(
        select(HorarioTrabalho).where(
            HorarioTrabalho.profissional_id == profissional_id,
            HorarioTrabalho.is_active.is_(True),
        ).order_by(HorarioTrabalho.dia_semana)
    )
    return list(result.scalars().all())


async def buscar_horario(db: AsyncSession, horario_id: str) -> HorarioTrabalho:
    result = await db.execute(
        select(HorarioTrabalho).where(HorarioTrabalho.id == horario_id)
    )
    horario = result.scalar_one_or_none()
    if horario is None:
        raise HTTPException(status_code=404, detail="Horário não encontrado")
    return horario


async def atualizar_horario(
    db: AsyncSession,
    horario_id: str,
    data: HorarioTrabalhoUpdate,
    admin: Usuario,
) -> HorarioTrabalho:
    horario = await buscar_horario(db, horario_id)
    await _verificar_dono(db, horario.profissional_id, admin)

    campos = data.model_dump(exclude_unset=True)
    for campo, valor in campos.items():
        setattr(horario, campo, valor)

    await db.commit()
    await db.refresh(horario)
    return horario


async def deletar_horario(
    db: AsyncSession, horario_id: str, admin: Usuario
) -> None:
    horario = await buscar_horario(db, horario_id)
    await _verificar_dono(db, horario.profissional_id, admin)

    # Horários não têm deleted_at — desativamos com is_active=False
    horario.is_active = False
    await db.commit()