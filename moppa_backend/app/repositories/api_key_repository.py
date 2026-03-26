import secrets
import hashlib
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import ApiKeyEntity
from app.models.api_key_model import ApiKeyCreateModel, ApiKeyUpdateModel


class ApiKeyRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    @staticmethod
    def generate_token() -> str:
        return f"sk-{secrets.token_hex(20)}"

    @staticmethod
    def hash_token(token: str) -> str:
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    def create(self, payload: ApiKeyCreateModel, created_by: UUID) -> tuple[ApiKeyEntity, str]:
        token = self.generate_token()
        token_hash = self.hash_token(token)
        token_prefix = token[:12]
        entity = ApiKeyEntity(
            name=payload.name.strip(),
            token=token,
            token_hash=token_hash,
            token_prefix=token_prefix,
            user_type=payload.user_type,
            purpose=payload.purpose.strip() if payload.purpose else None,
            is_active=True,
            created_by=created_by,
        )
        self.db.add(entity)
        self.db.flush()
        self.db.commit()
        self.db.refresh(entity)
        return entity, token

    def get_by_id(self, key_id: UUID) -> ApiKeyEntity | None:
        entity = self.db.get(ApiKeyEntity, key_id)
        if entity is None or entity.deleted_at is not None:
            return None
        return entity

    def get_by_token_hash(self, token_hash: str) -> ApiKeyEntity | None:
        return self.db.scalar(
            select(ApiKeyEntity).where(
                ApiKeyEntity.token_hash == token_hash,
                ApiKeyEntity.is_active.is_(True),
                ApiKeyEntity.deleted_at.is_(None),
            )
        )

    def name_exists(self, name: str, exclude_id: UUID | None = None) -> bool:
        query = select(func.count()).select_from(ApiKeyEntity).where(
            ApiKeyEntity.name == name.strip(),
            ApiKeyEntity.deleted_at.is_(None),
        )
        if exclude_id is not None:
            query = query.where(ApiKeyEntity.id != exclude_id)
        return (self.db.scalar(query) or 0) > 0

    def update(self, entity: ApiKeyEntity, payload: ApiKeyUpdateModel) -> ApiKeyEntity:
        if payload.name is not None:
            entity.name = payload.name.strip()
        if payload.user_type is not None:
            entity.user_type = payload.user_type
        if payload.purpose is not None:
            entity.purpose = payload.purpose.strip() if payload.purpose.strip() else None
        if payload.is_active is not None:
            entity.is_active = payload.is_active
        self.db.commit()
        self.db.refresh(entity)
        return entity

    def soft_delete(self, entity: ApiKeyEntity) -> None:
        entity.deleted_at = datetime.now(timezone.utc)
        entity.is_active = False
        self.db.commit()

    def update_last_used(self, entity: ApiKeyEntity) -> None:
        entity.last_used_at = datetime.now(timezone.utc)
        self.db.commit()

    def list_paginated(self, page: int, page_size: int) -> tuple[list[ApiKeyEntity], int]:
        offset = (page - 1) * page_size
        query = select(ApiKeyEntity).where(ApiKeyEntity.deleted_at.is_(None))
        total = self.db.scalar(
            select(func.count()).select_from(ApiKeyEntity).where(ApiKeyEntity.deleted_at.is_(None))
        )
        items = list(
            self.db.scalars(query.order_by(ApiKeyEntity.created_at.desc()).offset(offset).limit(page_size))
        )
        return items, int(total or 0)
