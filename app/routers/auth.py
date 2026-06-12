from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.session import get_db
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse
from app.schemas.user import UserPublic
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])

# Cookie path scoped tightly — browser only sends the cookie to this endpoint,
# not to every API request.
_COOKIE_PATH = "/api/v1/auth/refresh"
_COOKIE_MAX_AGE = settings.refresh_token_expire_days * 86400


def _set_refresh_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key="refresh_token",
        value=token,
        httponly=True,
        secure=False,  # set True in production (requires HTTPS)
        samesite="strict",
        max_age=_COOKIE_MAX_AGE,
        path=_COOKIE_PATH,
    )


@router.post("/register", response_model=TokenResponse, status_code=201)
async def register(
        data: RegisterRequest,
        response: Response,
        db: AsyncSession = Depends(get_db),
):
    access_token, refresh_token, usuario = await auth_service.register(db, data)
    _set_refresh_cookie(response, refresh_token)
    return TokenResponse(
        access_token=access_token,
        user=UserPublic.model_validate(usuario),
    )


@router.post("/login", response_model=TokenResponse)
async def login(
        data: LoginRequest,
        response: Response,
        db: AsyncSession = Depends(get_db),
):
    access_token, refresh_token, usuario = await auth_service.login(db, data)
    _set_refresh_cookie(response, refresh_token)
    return TokenResponse(
        access_token=access_token,
        user=UserPublic.model_validate(usuario),
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
        request: Request,
        response: Response,
        db: AsyncSession = Depends(get_db),
):
    refresh_token = request.cookies.get("refresh_token")
    if not refresh_token:
        raise HTTPException(status_code=401, detail="Refresh token ausente")

    new_access_token, usuario = await auth_service.refresh(db, refresh_token)
    # Re-set the cookie to renew its browser TTL
    _set_refresh_cookie(response, refresh_token)
    return TokenResponse(
        access_token=new_access_token,
        user=UserPublic.model_validate(usuario),
    )


@router.post("/logout", status_code=204)
async def logout(response: Response):
    # Path, httponly, samesite must match set_cookie exactly or browser ignores the clear
    response.delete_cookie(
        key="refresh_token",
        path=_COOKIE_PATH,
        httponly=True,
        secure=False,
        samesite="strict",
    )
