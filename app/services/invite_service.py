import secrets
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core import security
from app.core.config import settings
from app.models.professional import Professional
from app.models.professional_invite import ProfessionalInvite
from app.models.professional_store import ProfessionalStore
from app.models.user import RoleEnum, User
from app.schemas.invite import InviteAcceptRequest, InviteAcceptResponse, InviteCreatedResponse, InvitePublic
from app.services.store_service import get_store

_INVITE_TTL_HOURS = 24


async def create_invite(
    db: AsyncSession, store_id: str, admin: User
) -> InviteCreatedResponse:
    store = await get_store(db, store_id)

    if store.owner_id != admin.id:
        raise HTTPException(status_code=403, detail="Apenas o dono da loja pode gerar convites")

    token = secrets.token_urlsafe(32)
    expires_at = datetime.now(timezone.utc) + timedelta(hours=_INVITE_TTL_HOURS)

    invite = ProfessionalInvite(
        token=token,
        store_id=store_id,
        created_by=admin.id,
        expires_at=expires_at,
    )
    db.add(invite)
    await db.commit()

    url = f"{settings.frontend_url}/invite/{token}"
    return InviteCreatedResponse(token=token, url=url, expires_at=expires_at)


async def get_invite_by_token(db: AsyncSession, token: str) -> ProfessionalInvite:
    result = await db.execute(
        select(ProfessionalInvite).where(
            ProfessionalInvite.token == token,
            ProfessionalInvite.deleted_at.is_(None),
        )
    )
    invite = result.scalar_one_or_none()
    if invite is None:
        raise HTTPException(status_code=404, detail="Convite não encontrado")
    _assert_invite_usable(invite)
    return invite


async def get_invite_public(db: AsyncSession, token: str) -> InvitePublic:
    invite = await get_invite_by_token(db, token)
    store = await get_store(db, invite.store_id)
    return InvitePublic(
        store_id=store.id,
        store_name=store.name,
        expires_at=invite.expires_at,
    )


async def accept_invite(
    db: AsyncSession,
    token: str,
    current_user: User | None,
    body: InviteAcceptRequest,
) -> InviteAcceptResponse:
    # Lock the row to prevent race conditions on simultaneous accepts
    result = await db.execute(
        select(ProfessionalInvite)
        .where(
            ProfessionalInvite.token == token,
            ProfessionalInvite.deleted_at.is_(None),
        )
        .with_for_update()
    )
    invite = result.scalar_one_or_none()
    if invite is None:
        raise HTTPException(status_code=404, detail="Convite não encontrado")
    _assert_invite_usable(invite)

    access_token: str | None = None
    refresh_token: str | None = None

    if current_user is None:
        user, access_token, refresh_token = await _accept_anonymous(db, body)
    elif current_user.role == RoleEnum.client:
        user = await _accept_client(db, current_user)
    else:
        # professional or store_admin — role stays as-is
        user = current_user

    professional = await _upsert_professional(db, user)
    link = await _upsert_professional_store(db, professional.id, invite.store_id)

    invite.used_at = datetime.now(timezone.utc)
    invite.accepted_user_id = user.id
    await db.commit()

    result = await db.execute(
        select(ProfessionalStore)
        .options(selectinload(ProfessionalStore.store))
        .where(ProfessionalStore.id == link.id)
    )
    link = result.scalar_one()

    return InviteAcceptResponse(
        professional_store=link,
        access_token=access_token,
        refresh_token=refresh_token,
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _assert_invite_usable(invite: ProfessionalInvite) -> None:
    if invite.used_at is not None:
        raise HTTPException(status_code=409, detail="Convite já utilizado")
    if invite.expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=410, detail="Convite expirado")


async def _accept_anonymous(
    db: AsyncSession, body: InviteAcceptRequest
) -> tuple[User, str, str]:
    if not body.name or not body.email or not body.password:
        raise HTTPException(
            status_code=422,
            detail="name, email e password são obrigatórios para criar uma conta",
        )
    if not body.accepted_terms:
        raise HTTPException(status_code=422, detail="É necessário aceitar os termos de uso")

    existing = await db.execute(
        select(User).where(User.email == body.email, User.deleted_at.is_(None))
    )
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(status_code=409, detail="Email já cadastrado")

    user = User(
        name=body.name,
        email=body.email,
        password_hash=security.hash_password(body.password),
        phone=body.phone,
        role=RoleEnum.professional,
        accepted_terms_at=datetime.now(timezone.utc),
        accepted_terms_version=settings.current_terms_version,
    )
    db.add(user)
    await db.flush()

    access_token = security.create_access_token({"sub": user.id, "role": user.role})
    refresh_token = security.create_refresh_token({"sub": user.id})
    return user, access_token, refresh_token


async def _accept_client(db: AsyncSession, user: User) -> User:
    user.role = RoleEnum.professional
    await db.flush()
    return user


async def _upsert_professional(db: AsyncSession, user: User) -> Professional:
    result = await db.execute(
        select(Professional).where(
            Professional.user_id == user.id,
            Professional.deleted_at.is_(None),
        )
    )
    professional = result.scalar_one_or_none()
    if professional is None:
        professional = Professional(user_id=user.id)
        db.add(professional)
        await db.flush()
    return professional


async def _upsert_professional_store(
    db: AsyncSession, professional_id: str, store_id: str
) -> ProfessionalStore:
    result = await db.execute(
        select(ProfessionalStore).where(
            ProfessionalStore.professional_id == professional_id,
            ProfessionalStore.store_id == store_id,
        )
    )
    link = result.scalar_one_or_none()

    if link is not None and link.deleted_at is None:
        raise HTTPException(status_code=409, detail="Profissional já vinculado a esta loja")

    if link is not None:
        link.deleted_at = None
        link.is_active = True
    else:
        link = ProfessionalStore(professional_id=professional_id, store_id=store_id)
        db.add(link)

    await db.flush()
    return link
