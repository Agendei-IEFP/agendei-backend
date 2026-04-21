from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException

from app.models.loja import Loja
from app.models.usuario import Usuario, RoleEnum
from app.schemas.loja import LojaCreate, LojaUpdate


async def criar_loja(db: AsyncSession, data: LojaCreate, owner: Usuario) -> Loja:
    """
    Só admin_loja pode criar. O owner é o usuário autenticado —
    não precisa vir no body, evitamos que alguém crie lojas no nome de outro.
    """
    if owner.role != RoleEnum.admin_loja:
        raise HTTPException(status_code=403, detail="Apenas admin_loja pode criar lojas")

    loja = Loja(
        nome=data.nome,
        descricao=data.descricao,
        telefone=data.telefone,
        endereco=data.endereco,
        cidade=data.cidade,
        estado=data.estado,
        owner_id=owner.id,
    )
    db.add(loja)
    await db.commit()
    await db.refresh(loja)
    return loja


async def listar_lojas(db: AsyncSession) -> list[Loja]:
    """Lista todas as lojas ativas (não deletadas). Rota pública."""
    result = await db.execute(
        select(Loja).where(
            Loja.deleted_at.is_(None),
            Loja.is_active.is_(True),
        )
    )
    return list(result.scalars().all())


async def buscar_loja(db: AsyncSession, loja_id: str) -> Loja:
    """Busca uma loja pelo ID. Levanta 404 se não existir."""
    result = await db.execute(
        select(Loja).where(
            Loja.id == loja_id,
            Loja.deleted_at.is_(None),
        )
    )
    loja = result.scalar_one_or_none()
    if loja is None:
        raise HTTPException(status_code=404, detail="Loja não encontrada")
    return loja


async def atualizar_loja(
    db: AsyncSession,
    loja_id: str,
    data: LojaUpdate,
    usuario: Usuario,
) -> Loja:
    """
    Só o dono da loja pode atualizar.
    Usamos model_dump(exclude_unset=True) para não sobrescrever campos
    que o cliente não enviou — PATCH semântico.
    """
    loja = await buscar_loja(db, loja_id)

    if loja.owner_id != usuario.id:
        raise HTTPException(status_code=403, detail="Apenas o dono da loja pode editá-la")

    campos = data.model_dump(exclude_unset=True)
    for campo, valor in campos.items():
        setattr(loja, campo, valor)

    await db.commit()
    await db.refresh(loja)
    return loja


async def deletar_loja(db: AsyncSession, loja_id: str, usuario: Usuario) -> None:
    """
    Soft delete: não apagamos o registro, apenas setamos deleted_at.
    Preserva histórico de agendamentos vinculados à loja.
    """
    from datetime import datetime, timezone

    loja = await buscar_loja(db, loja_id)

    if loja.owner_id != usuario.id:
        raise HTTPException(status_code=403, detail="Apenas o dono da loja pode deletá-la")

    loja.deleted_at = datetime.now(timezone.utc)
    await db.commit()