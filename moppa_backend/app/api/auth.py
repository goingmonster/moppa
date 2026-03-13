from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.db.models import AppUserEntity
from app.db.session import get_db
from app.models.auth_model import (
    AuthLoginRequest,
    AuthLoginResponse,
    AuthRefreshRequest,
    AuthRegisterRequest,
    AuthTokenPairResponse,
    AuthUserResponse,
)
from app.repositories.auth_repository import AuthRepository
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", summary="Register user")
def register(payload: AuthRegisterRequest, db: Session = Depends(get_db)) -> AuthUserResponse:
    service = AuthService(AuthRepository(db))
    return service.register(payload)


@router.post("/login", summary="Login")
def login(payload: AuthLoginRequest, db: Session = Depends(get_db)) -> AuthLoginResponse:
    service = AuthService(AuthRepository(db))
    return service.login(payload.username, payload.password)


@router.post("/refresh", summary="Refresh token")
def refresh(payload: AuthRefreshRequest, db: Session = Depends(get_db)) -> AuthLoginResponse:
    service = AuthService(AuthRepository(db))
    return service.refresh(payload.refresh_token)


@router.post("/logout", summary="Logout")
def logout(payload: AuthRefreshRequest, db: Session = Depends(get_db)) -> dict[str, str]:
    service = AuthService(AuthRepository(db))
    service.logout(payload.refresh_token)
    return {"status": "ok"}


@router.get("/me", summary="Current user")
def me(current_user: AppUserEntity = Depends(get_current_user)) -> AuthUserResponse:
    return AuthUserResponse(
        id=str(current_user.id),
        username=current_user.username,
        role=current_user.role,
        is_active=current_user.is_active,
    )
