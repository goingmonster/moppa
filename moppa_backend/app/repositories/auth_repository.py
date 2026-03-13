from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.db.models import AppUserEntity, AuthRefreshTokenEntity


class AuthRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_user_by_username(self, username: str) -> AppUserEntity | None:
        normalized = username.strip()
        if not normalized:
            return None
        return self.db.scalar(
            select(AppUserEntity).where(
                AppUserEntity.username == normalized,
                AppUserEntity.deleted_at.is_(None),
            )
        )

    def get_user_by_id(self, user_id: UUID) -> AppUserEntity | None:
        entity = self.db.get(AppUserEntity, user_id)
        if entity is None or entity.deleted_at is not None:
            return None
        return entity

    def create_user(self, username: str, password_hash: str, role: str, email: str | None) -> AppUserEntity:
        entity = AppUserEntity(
            username=username.strip(),
            password_hash=password_hash,
            role=role,
            email=email.strip() if email else None,
            is_active=True,
            permissions={},
        )
        self.db.add(entity)
        self.db.commit()
        self.db.refresh(entity)
        return entity

    def has_any_active_user(self) -> bool:
        row = self.db.scalar(
            select(AppUserEntity.id).where(
                AppUserEntity.deleted_at.is_(None),
            ).limit(1)
        )
        return row is not None

    def update_last_login_at(self, user_id: UUID) -> None:
        entity = self.db.get(AppUserEntity, user_id)
        if entity is None:
            return
        entity.last_login_at = datetime.now(timezone.utc)
        self.db.commit()

    def create_refresh_token(self, user_id: UUID, token_hash: str, expires_at: datetime) -> None:
        entity = AuthRefreshTokenEntity(
            user_id=user_id,
            token_hash=token_hash,
            expires_at=expires_at,
        )
        self.db.add(entity)
        self.db.commit()

    def get_refresh_token(self, token_hash: str) -> AuthRefreshTokenEntity | None:
        return self.db.scalar(select(AuthRefreshTokenEntity).where(AuthRefreshTokenEntity.token_hash == token_hash))

    def revoke_refresh_token(self, token_hash: str) -> None:
        entity = self.get_refresh_token(token_hash)
        if entity is None or entity.revoked_at is not None:
            return
        entity.revoked_at = datetime.now(timezone.utc)
        self.db.commit()

    def revoke_all_user_refresh_tokens(self, user_id: UUID) -> None:
        rows = list(self.db.scalars(select(AuthRefreshTokenEntity).where(AuthRefreshTokenEntity.user_id == user_id)))
        now = datetime.now(timezone.utc)
        changed = False
        for row in rows:
            if row.revoked_at is None:
                row.revoked_at = now
                changed = True
        if changed:
            self.db.commit()

    def delete_expired_refresh_tokens(self) -> None:
        now = datetime.now(timezone.utc)
        self.db.execute(
            delete(AuthRefreshTokenEntity).where(
                AuthRefreshTokenEntity.expires_at < now,
            )
        )
        self.db.commit()
