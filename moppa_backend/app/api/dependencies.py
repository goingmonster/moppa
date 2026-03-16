from uuid import UUID

from fastapi import Depends, Header
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.core import ApiError
from app.db.models import AppUserEntity
from app.db.session import get_db
from app.repositories.auth_repository import AuthRepository
from app.security.auth import decode_access_token, is_integration_api_token


def _extract_bearer_token(authorization: str | None) -> str:
    if authorization is None:
        raise ApiError(status_code=401, code="AUTH_REQUIRED", message="Missing authorization header")
    prefix = "Bearer "
    if not authorization.startswith(prefix):
        raise ApiError(status_code=401, code="INVALID_AUTH_HEADER", message="Invalid authorization header")
    return authorization[len(prefix) :].strip()


def _resolve_system_admin_user(db: Session, preferred_username: str) -> AppUserEntity:
    repository = AuthRepository(db)
    preferred = repository.get_user_by_username(preferred_username)
    if preferred is not None and preferred.is_active and preferred.deleted_at is None and preferred.role == "admin":
        return preferred

    fallback = db.scalar(
        select(AppUserEntity)
        .where(
            AppUserEntity.role == "admin",
            AppUserEntity.is_active.is_(True),
            AppUserEntity.deleted_at.is_(None),
        )
        .order_by(AppUserEntity.created_at.asc())
        .limit(1)
    )
    if fallback is not None:
        return fallback

    raise ApiError(
        status_code=503,
        code="SYSTEM_ADMIN_USER_NOT_FOUND",
        message="No active admin user found for system authentication mode",
    )


def get_current_user(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> AppUserEntity:
    if not settings.auth_enabled:
        return _resolve_system_admin_user(db, preferred_username="dev-admin")

    token = _extract_bearer_token(authorization)
    if is_integration_api_token(token):
        return _resolve_system_admin_user(db, preferred_username="integration-admin")

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
