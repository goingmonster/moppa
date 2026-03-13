from datetime import datetime, timezone
from uuid import UUID

from app.core import ApiError
from app.models.auth_model import AuthLoginResponse, AuthRegisterRequest, AuthUserResponse
from app.repositories.auth_repository import AuthRepository
from app.security.auth import (
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
    hash_password,
    hash_refresh_token,
    verify_password,
)


class AuthService:
    def __init__(self, repository: AuthRepository) -> None:
        self.repository = repository

    def register(self, payload: AuthRegisterRequest) -> AuthUserResponse:
        existing = self.repository.get_user_by_username(payload.username)
        if existing is not None:
            raise ApiError(status_code=409, code="USERNAME_ALREADY_EXISTS", message="Username already exists")

        role = "admin" if not self.repository.has_any_active_user() else "operator"

        entity = self.repository.create_user(
            username=payload.username,
            password_hash=hash_password(payload.password),
            role=role,
            email=payload.email,
        )
        return self._to_user_response(entity.id, entity.username, entity.role, entity.is_active)

    def login(self, username: str, password: str) -> AuthLoginResponse:
        entity = self.repository.get_user_by_username(username)
        if entity is None or not verify_password(password, entity.password_hash):
            raise ApiError(status_code=401, code="INVALID_CREDENTIALS", message="Invalid username or password")
        if not entity.is_active:
            raise ApiError(status_code=403, code="USER_DISABLED", message="User is disabled")

        access_token = create_access_token(user_id=str(entity.id), role=entity.role)
        refresh_token, refresh_expires_at = create_refresh_token(user_id=str(entity.id))
        self.repository.create_refresh_token(
            user_id=entity.id,
            token_hash=hash_refresh_token(refresh_token),
            expires_at=refresh_expires_at,
        )
        self.repository.update_last_login_at(entity.id)
        self.repository.delete_expired_refresh_tokens()
        return AuthLoginResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            user=self._to_user_response(entity.id, entity.username, entity.role, entity.is_active),
        )

    def refresh(self, refresh_token: str) -> AuthLoginResponse:
        try:
            payload = decode_refresh_token(refresh_token)
        except ValueError as exc:
            raise ApiError(status_code=401, code="INVALID_REFRESH_TOKEN", message="Invalid refresh token") from exc

        token_hash = hash_refresh_token(refresh_token)
        token_entity = self.repository.get_refresh_token(token_hash)
        if token_entity is None or token_entity.revoked_at is not None:
            raise ApiError(status_code=401, code="REFRESH_TOKEN_REVOKED", message="Refresh token revoked")
        if token_entity.expires_at <= datetime.now(timezone.utc):
            raise ApiError(status_code=401, code="REFRESH_TOKEN_EXPIRED", message="Refresh token expired")

        sub = payload.get("sub")
        if not isinstance(sub, str):
            raise ApiError(status_code=401, code="INVALID_REFRESH_TOKEN", message="Invalid refresh token")

        user = self.repository.get_user_by_id(UUID(sub))
        if user is None or not user.is_active:
            raise ApiError(status_code=401, code="USER_NOT_AVAILABLE", message="User not available")

        access_token = create_access_token(user_id=str(user.id), role=user.role)
        new_refresh_token, new_refresh_expires_at = create_refresh_token(user_id=str(user.id))
        self.repository.revoke_refresh_token(token_hash)
        self.repository.create_refresh_token(
            user_id=user.id,
            token_hash=hash_refresh_token(new_refresh_token),
            expires_at=new_refresh_expires_at,
        )

        return AuthLoginResponse(
            access_token=access_token,
            refresh_token=new_refresh_token,
            user=self._to_user_response(user.id, user.username, user.role, user.is_active),
        )

    def logout(self, refresh_token: str) -> None:
        token_hash = hash_refresh_token(refresh_token)
        self.repository.revoke_refresh_token(token_hash)

    @staticmethod
    def _to_user_response(user_id: UUID, username: str, role: str, is_active: bool) -> AuthUserResponse:
        return AuthUserResponse(
            id=str(user_id),
            username=username,
            role=role,
            is_active=is_active,
        )
