from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException

from app.models.servico import Servico
from app.models.usuario import Usuario
from app.schemas.servico import ServicoCreate, ServicoUpdate
from app.services.profissional_service import buscar_profissional
from app.services.loja_service import buscar_loja


async def _verificar_dono(db: AsyncSession, profissional_id: str, admin: Usuario) -> None:
    """Verifica se o admin é dono da loja do profissional."""
    profissional = await buscar_profissional(db, profissional_id)
    loja = await buscar_loja(db, profissional.loja_id)
    if loja.owner_id != admin.id:
        raise HTTPException(status_code=403, detail="Acesso negado")


async def criar_servico(
    db: AsyncSession,
    profissional_id: str,
    data: ServicoCreate,
    admin: Usuario,
) -> Servico:
    await _verificar_dono(db, profissional_id, admin)

    servico = Servico(
        profissional_id=profissional_id,
        nome=data.nome,
        descricao=data.descricao,
        preco=data.preco,
        duracao_minutos=data.duracao_minutos,
    )
    db.add(servico)
    await db.commit()
    await db.refresh(servico)
    return servico


async def listar_servicos_do_profissional(
    db: AsyncSession, profissional_id: str
) -> list[Servico]:
    """Rota pública — clientes precisam ver os serviços disponíveis."""
    await buscar_profissional(db, profissional_id)  # garante que existe
    result = await db.execute(
        select(Servico).where(
            Servico.profissional_id == profissional_id,
            Servico.deleted_at.is_(None),
            Servico.is_active.is_(True),
        )
    )
    return list(result.scalars().all())


async def buscar_servico(db: AsyncSession, servico_id: str) -> Servico:
    result = await db.execute(
        select(Servico).where(
            Servico.id == servico_id,
            Servico.deleted_at.is_(None),
        )
    )
    servico = result.scalar_one_or_none()
    if servico is None:
        raise HTTPException(status_code=404, detail="Serviço não encontrado")
    return servico


async def atualizar_servico(
    db: AsyncSession,
    servico_id: str,
    data: ServicoUpdate,
    admin: Usuario,
) -> Servico:
    servico = await buscar_servico(db, servico_id)
    await _verificar_dono(db, servico.profissional_id, admin)

    campos = data.model_dump(exclude_unset=True)
    for campo, valor in campos.items():
        setattr(servico, campo, valor)

    await db.commit()
    await db.refresh(servico)
    return servico


async def deletar_servico(
    db: AsyncSession, servico_id: str, admin: Usuario
) -> None:
    from datetime import datetime, timezone

    servico = await buscar_servico(db, servico_id)
    await _verificar_dono(db, servico.profissional_id, admin)

    servico.deleted_at = datetime.now(timezone.utc)
    await db.commit()