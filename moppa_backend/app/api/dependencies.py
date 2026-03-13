from uuid import UUID

from fastapi import Depends, Header
from sqlalchemy.orm import Session

from app.config import settings
from app.core import ApiError
from app.db.models import AppUserEntity
from app.db.session import get_db
from app.repositories.auth_repository import AuthRepository
from app.security.auth import decode_access_token


def _extract_bearer_token(authorization: str | None) -> str:
    if authorization is None:
        raise ApiError(status_code=401, code="AUTH_REQUIRED", message="Missing authorization header")
    prefix = "Bearer "
    if not authorization.startswith(prefix):
        raise ApiError(status_code=401, code="INVALID_AUTH_HEADER", message="Invalid authorization header")
    return authorization[len(prefix) :].strip()


def get_current_user(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> AppUserEntity:
    if not settings.auth_enabled:
        mock_user = AppUserEntity(
            id=UUID("00000000-0000-0000-0000-000000000001"),
            username="dev-admin",
            role="admin",
            password_hash="",
            email=None,
            is_active=True,
            permissions={},
            last_login_at=None,
            deleted_at=None,
        )
        return mock_user

    token = _extract_bearer_token(authorization)
    try:
        payload = decode_access_token(token)
    except ValueError as exc:
        raise ApiError(status_code=401, code="INVALID_ACCESS_TOKEN", message="Invalid access token") from exc

    sub = payload.get("sub")
    if not isinstance(sub, str):
        raise ApiError(status_code=401, code="INVALID_ACCESS_TOKEN", message="Invalid access token")

    repository = AuthRepository(db)
    user = repository.get_user_by_id(UUID(sub))
    if user is None or user.deleted_at is not None:
        raise ApiError(status_code=401, code="USER_NOT_FOUND", message="User not found")
    if not user.is_active:
        raise ApiError(status_code=403, code="USER_DISABLED", message="User is disabled")
    return user


def require_admin_user(current_user: AppUserEntity = Depends(get_current_user)) -> AppUserEntity:
    if current_user.role != "admin":
        raise ApiError(status_code=403, code="FORBIDDEN", message="Admin role required")
    return current_user
