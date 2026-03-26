from uuid import UUID

from sqlalchemy.orm import Session

from app.core import ApiError
from app.db.models import ApiKeyEntity
from app.models.api_key_model import (
    ApiKeyCreateModel,
    ApiKeyListItemModel,
    ApiKeyPaginationResponse,
    ApiKeyUpdateModel,
)
from app.repositories.api_key_repository import ApiKeyRepository


class ApiKeyService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repository = ApiKeyRepository(db)

    def create(self, payload: ApiKeyCreateModel, created_by: UUID) -> tuple[ApiKeyEntity, str]:
        if self.repository.name_exists(payload.name):
            raise ApiError(status_code=409, code="NAME_EXISTS", message="用户名称已存在，请使用其他名称")
        entity, token = self.repository.create(payload, created_by)
        return entity, token

    def list_paginated(self, page: int, page_size: int) -> ApiKeyPaginationResponse:
        items, total = self.repository.list_paginated(page=page, page_size=page_size)
        return ApiKeyPaginationResponse(
            page=page,
            page_size=page_size,
            total=total,
            items=[self._to_list_item(item) for item in items],
        )

    def get_by_id(self, key_id: str) -> ApiKeyEntity:
        entity = self.repository.get_by_id(UUID(key_id))
        if entity is None:
            raise ApiError(status_code=404, code="API_KEY_NOT_FOUND", message="API Key not found")
        return entity

    def update(self, key_id: str, payload: ApiKeyUpdateModel, current_user_id: UUID) -> ApiKeyEntity:
        entity = self.get_by_id(key_id)
        if payload.name is not None and self.repository.name_exists(payload.name, exclude_id=entity.id):
            raise ApiError(status_code=409, code="NAME_EXISTS", message="用户名称已存在，请使用其他名称")
        return self.repository.update(entity, payload)

    def delete(self, key_id: str) -> None:
        entity = self.get_by_id(key_id)
        self.repository.soft_delete(entity)

    @staticmethod
    def _to_list_item(entity: ApiKeyEntity) -> ApiKeyListItemModel:
        return ApiKeyListItemModel(
            id=str(entity.id),
            name=entity.name,
            token=entity.token,
            user_type=entity.user_type,
            purpose=entity.purpose,
            is_active=entity.is_active,
            last_used_at=entity.last_used_at.isoformat() if entity.last_used_at else None,
            created_by=str(entity.created_by) if entity.created_by else None,
            created_at=entity.created_at.isoformat(),
        )
