from datetime import datetime, timezone

from fastapi import HTTPException
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import security
from app.core.config import settings
from app.models.user import User
from app.schemas.auth import LoginRequest, RegisterRequest


async def register(db: AsyncSession, data: RegisterRequest) -> tuple[str, str, User]:
    result = await db.execute(
        select(User).where(
            User.email == data.email,
            User.deleted_at.is_(None),
        )
    )
    if result.scalar_one_or_none() is not None:
        raise HTTPException(status_code=409, detail="Email já cadastrado")

    user = User(
        name=data.name,
        email=data.email,
        password_hash=security.hash_password(data.password),
        role=data.role,
        phone=data.phone,
        accepted_terms_at=datetime.now(timezone.utc),
        accepted_terms_version=settings.current_terms_version,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    access_token = security.create_access_token({"sub": user.id, "role": user.role})
    refresh_token = security.create_refresh_token({"sub": user.id})
    return access_token, refresh_token, user


async def login(
        db: AsyncSession, data: LoginRequest
) -> tuple[str, str, User]:
    result = await db.execute(
        select(User).where(
            User.email == data.email,
            User.deleted_at.is_(None),
        )
    )
    user = result.scalar_one_or_none()

    if user is None or not security.verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Credenciais inválidas")

    access_token = security.create_access_token({"sub": user.id, "role": user.role})
    refresh_token = security.create_refresh_token({"sub": user.id})
    return access_token, refresh_token, user


async def refresh(
        db: AsyncSession, refresh_token: str
) -> tuple[str, User]:
    try:
        payload = security.decode_token(refresh_token)
    except JWTError:
        raise HTTPException(status_code=401, detail="Token de refresh inválido ou expirado")

    user_id: str | None = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Token inválido")

    result = await db.execute(
        select(User).where(
            User.id == user_id,
            User.deleted_at.is_(None),
        )
    )
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=401, detail="Usuário não encontrado")

    access_token = security.create_access_token({"sub": user.id, "role": user.role})
    return access_token, user
