from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_optional_user, require_role
from app.db.session import get_db
from app.models.user import RoleEnum, User
from app.schemas.invite import InviteAcceptRequest, InviteAcceptResponse, InviteCreatedResponse, InvitePublic
from app.services import invite_service

router = APIRouter(tags=["invites"])


@router.post(
    "/stores/{store_id}/invites",
    response_model=InviteCreatedResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_invite(
        store_id: str,
        db: AsyncSession = Depends(get_db),
        admin: User = Depends(require_role(RoleEnum.store_admin)),
):
    return await invite_service.create_invite(db, store_id, admin)


@router.get("/invites/{token}", response_model=InvitePublic)
async def get_invite(token: str, db: AsyncSession = Depends(get_db)):
    return await invite_service.get_invite_public(db, token)


@router.post("/invites/{token}/accept", response_model=InviteAcceptResponse)
async def accept_invite(
        token: str,
        body: InviteAcceptRequest = InviteAcceptRequest(),
        db: AsyncSession = Depends(get_db),
        current_user: User | None = Depends(get_optional_user),
):
    return await invite_service.accept_invite(db, token, current_user, body)
