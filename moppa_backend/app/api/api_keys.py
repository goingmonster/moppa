from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.dependencies import require_admin_user
from app.db.models import AppUserEntity
from app.db.session import get_db
from app.models.api_key_model import (
    ApiKeyCreateModel,
    ApiKeyListItemModel,
    ApiKeyPaginationResponse,
    ApiKeyUpdateModel,
)
from app.services.api_key_service import ApiKeyService

router = APIRouter(prefix="/api-keys", tags=["api-keys"], dependencies=[Depends(require_admin_user)])


@router.post("", summary="Create API key")
def create_api_key(
    payload: ApiKeyCreateModel,
    current_user: AppUserEntity = Depends(require_admin_user),
    db: Session = Depends(get_db),
) -> dict[str, str | None]:
    service = ApiKeyService(db)
    entity, token = service.create(payload, created_by=current_user.id)
    return {
        "id": str(entity.id),
        "name": entity.name,
        "token": token,
        "user_type": entity.user_type,
        "purpose": entity.purpose,
    }


@router.get("", summary="List API keys")
def list_api_keys(
    page: int = 1,
    page_size: int = 20,
    db: Session = Depends(get_db),
) -> ApiKeyPaginationResponse:
    service = ApiKeyService(db)
    return service.list_paginated(page=page, page_size=page_size)


@router.get("/{key_id}", summary="Get API key detail")
def get_api_key(
    key_id: str,
    db: Session = Depends(get_db),
) -> ApiKeyListItemModel:
    service = ApiKeyService(db)
    entity = service.get_by_id(key_id)
    return service._to_list_item(entity)


@router.patch("/{key_id}", summary="Update API key")
def update_api_key(
    key_id: str,
    payload: ApiKeyUpdateModel,
    current_user: AppUserEntity = Depends(require_admin_user),
    db: Session = Depends(get_db),
) -> ApiKeyListItemModel:
    service = ApiKeyService(db)
    entity = service.update(key_id, payload, current_user_id=current_user.id)
    return service._to_list_item(entity)


@router.delete("/{key_id}", summary="Delete API key")
def delete_api_key(
    key_id: str,
    db: Session = Depends(get_db),
) -> dict[str, str]:
    service = ApiKeyService(db)
    service.delete(key_id)
    return {"message": "API key deleted"}
