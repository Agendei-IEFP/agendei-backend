from datetime import datetime, timezone

from fastapi import HTTPException
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import security
from app.core.config import settings
from app.models.usuario import Usuario
from app.schemas.auth import LoginRequest, RegisterRequest


async def register(db: AsyncSession, data: RegisterRequest) -> Usuario:
    result = await db.execute(
        select(Usuario).where(
            Usuario.email == data.email,
            Usuario.deleted_at.is_(None),
        )
    )
    if result.scalar_one_or_none() is not None:
        raise HTTPException(status_code=409, detail="Email já cadastrado")

    usuario = Usuario(
        nome=data.nome,
        email=data.email,
        senha_hash=security.hash_password(data.password),
        role=data.role,
        telefone=data.telefone,
        accepted_terms_at=datetime.now(timezone.utc),
        accepted_terms_version=settings.current_terms_version,
    )
    db.add(usuario)
    await db.commit()
    await db.refresh(usuario)
    return usuario


async def login(
    db: AsyncSession, data: LoginRequest
) -> tuple[str, str, Usuario]:
    result = await db.execute(
        select(Usuario).where(
            Usuario.email == data.email,
            Usuario.deleted_at.is_(None),
        )
    )
    usuario = result.scalar_one_or_none()

    # Same message whether email doesn't exist or password is wrong —
    # nunca revelar qual o valor que estava incorreto no login.
    if usuario is None or not security.verify_password(data.password, usuario.senha_hash):
        raise HTTPException(status_code=401, detail="Credenciais inválidas")

    access_token = security.create_access_token(
        {"sub": usuario.id, "role": usuario.role}
    )
    refresh_token = security.create_refresh_token({"sub": usuario.id})
    return access_token, refresh_token, usuario


async def refresh(
    db: AsyncSession, refresh_token: str
) -> tuple[str, Usuario]:
    try:
        payload = security.decode_token(refresh_token)
    except JWTError:
        raise HTTPException(status_code=401, detail="Token de refresh inválido ou expirado")

    user_id: str | None = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Token inválido")

    result = await db.execute(
        select(Usuario).where(
            Usuario.id == user_id,
            Usuario.deleted_at.is_(None),
        )
    )
    usuario = result.scalar_one_or_none()
    if usuario is None:
        raise HTTPException(status_code=401, detail="Usuário não encontrado")

    access_token = security.create_access_token(
        {"sub": usuario.id, "role": usuario.role}
    )
    return access_token, usuario
