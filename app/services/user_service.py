from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password, verify_password
from app.models.user import User
from app.schemas.user import PasswordChange, UserUpdate


async def update_user(db: AsyncSession, user: User, data: UserUpdate) -> User:
    updates = data.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(user, field, value)
    await db.commit()
    await db.refresh(user)
    return user


async def change_password(db: AsyncSession, user: User, data: PasswordChange) -> None:
    if not verify_password(data.current_password, user.password_hash):
        raise HTTPException(status_code=400, detail="Senha atual incorreta")
    user.password_hash = hash_password(data.new_password)
    await db.commit()


async def anonymize_user(db: AsyncSession, user: User) -> None:
    now = datetime.now(timezone.utc)
    user.name = "Usuário anonimizado"
    user.email = f"anon_{user.id}@deleted.invalid"
    user.phone = None
    user.anonymized_at = now
    user.deleted_at = now
    await db.commit()


async def delete_user(db: AsyncSession, user: User) -> None:
    user.deleted_at = datetime.now(timezone.utc)
    await db.commit()
