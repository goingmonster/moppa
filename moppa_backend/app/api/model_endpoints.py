from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core import ApiError
from app.api.dependencies import require_admin_user
from app.db.session import get_db
from app.models.common_model import BatchDeleteRequest, BatchDeleteResponse
from app.models.model_endpoint_model import (
    ModelEndpointCreateModel,
    ModelEndpointListItemModel,
    ModelEndpointPaginationResponse,
    ModelEndpointUpdateModel,
)
from app.repositories.model_endpoint_repository import ModelEndpointRepository
from app.services.model_endpoint_service import ModelEndpointService

router = APIRouter(prefix="/model-endpoints", tags=["model-endpoints"], dependencies=[Depends(require_admin_user)])


def to_model_endpoint_item(row: dict[str, Any]) -> ModelEndpointListItemModel:
    created_at_raw = row.get("created_at")
    updated_at_raw = row.get("updated_at")
    return ModelEndpointListItemModel(
        id=str(row["id"]),
        name=str(row["name"]),
        identifier=str(row["identifier"]),
        provider=str(row["provider"]),
        endpoint_url=str(row["endpoint_url"]),
        api_key_ref=str(row["api_key_ref"]) if row["api_key_ref"] is not None else None,
        model_name=str(row["model_name"]),
        model_version=str(row["model_version"]),
        max_tokens=int(row["max_tokens"]),
        temperature=float(row["temperature"]),
        timeout_seconds=int(row["timeout_seconds"]),
        is_available=bool(row["is_available"]),
        status=str(row["status"]),
        created_at=created_at_raw.isoformat() if isinstance(created_at_raw, datetime) else "",
        updated_at=updated_at_raw.isoformat() if isinstance(updated_at_raw, datetime) else "",
    )


@router.post("", summary="Create model endpoint")
def create_model_endpoint(payload: ModelEndpointCreateModel, db: Session = Depends(get_db)) -> dict[str, str]:
    service = ModelEndpointService(ModelEndpointRepository(db))
    created = service.create(payload)
    return {"id": str(created["id"])}


@router.get("", summary="List model endpoints")
def list_model_endpoints(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> ModelEndpointPaginationResponse:
    service = ModelEndpointService(ModelEndpointRepository(db))
    rows, total = service.list_paginated(page=page, page_size=page_size)
    items = [to_model_endpoint_item(row) for row in rows]
    return ModelEndpointPaginationResponse(page=page, page_size=page_size, total=total, items=items)


@router.get("/{endpoint_id}", summary="Get model endpoint detail")
def get_model_endpoint(endpoint_id: str, db: Session = Depends(get_db)) -> ModelEndpointListItemModel:
    service = ModelEndpointService(ModelEndpointRepository(db))
    row = service.get_by_id(endpoint_id)
    if row is None:
        raise ApiError(status_code=404, code="MODEL_ENDPOINT_NOT_FOUND", message="Model endpoint not found")
    return to_model_endpoint_item(row)


@router.patch("/{endpoint_id}", summary="Update model endpoint")
def update_model_endpoint(
    endpoint_id: str,
    payload: ModelEndpointUpdateModel,
    db: Session = Depends(get_db),
) -> ModelEndpointListItemModel:
    if not payload.model_dump(exclude_none=True):
        raise ApiError(status_code=400, code="EMPTY_UPDATE_PAYLOAD", message="No fields to update")
    service = ModelEndpointService(ModelEndpointRepository(db))
    row = service.update(endpoint_id, payload)
    if row is None:
        raise ApiError(status_code=404, code="MODEL_ENDPOINT_NOT_FOUND", message="Model endpoint not found")
    return to_model_endpoint_item(row)


@router.delete("", summary="Batch delete model endpoints")
def delete_model_endpoints(payload: BatchDeleteRequest, db: Session = Depends(get_db)) -> BatchDeleteResponse:
    service = ModelEndpointService(ModelEndpointRepository(db))
    deleted_count = service.batch_delete(payload.ids)
    return BatchDeleteResponse(deleted_count=deleted_count)
