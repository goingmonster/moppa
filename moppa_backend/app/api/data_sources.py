from datetime import timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core import ApiError
from app.db.session import get_db
from app.models.common_model import BatchDeleteRequest, BatchDeleteResponse
from app.models.data_source_model import (
    DataSourceCreateModel,
    DataSourceListItemModel,
    DataSourcePaginationResponse,
    DataSourceUpdateModel,
)
from app.repositories.data_source_repository import DataSourceRepository
from app.services.data_source_service import DataSourceService

router = APIRouter(prefix="/data-sources", tags=["data-sources"])


def _format_interval(value: object) -> str:
    if isinstance(value, timedelta):
        total_seconds = int(value.total_seconds())
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        if minutes == 0:
            return f"{hours} hours"
        return f"{hours} hours {minutes} minutes"
    return str(value)


def to_data_source_item(row: dict[str, object]) -> DataSourceListItemModel:
    return DataSourceListItemModel(
        id=str(row["id"]),
        name=str(row["name"]),
        source_system=str(row["source_system"]),
        source_type=str(row["source_type"]),
        connection_config=dict(row["connection_config"] or {}),
        secret_ref=str(row["secret_ref"]) if row["secret_ref"] is not None else None,
        credibility_level=int(row["credibility_level"]),
        sync_frequency=_format_interval(row["sync_frequency"]),
        is_active=bool(row["is_active"]),
        version=str(row["version"]),
        created_at=row["created_at"].isoformat(),
        updated_at=row["updated_at"].isoformat(),
    )


@router.post("", summary="Create data source")
def create_data_source(payload: DataSourceCreateModel, db: Session = Depends(get_db)) -> dict[str, str]:
    service = DataSourceService(DataSourceRepository(db))
    created = service.create(payload)
    return {"id": str(created["id"])}


@router.get("", summary="List data sources")
def list_data_sources(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> DataSourcePaginationResponse:
    service = DataSourceService(DataSourceRepository(db))
    rows, total = service.list_paginated(page=page, page_size=page_size)
    items = [to_data_source_item(row) for row in rows]
    return DataSourcePaginationResponse(page=page, page_size=page_size, total=total, items=items)


@router.get("/{source_id}", summary="Get data source detail")
def get_data_source(source_id: str, db: Session = Depends(get_db)) -> DataSourceListItemModel:
    service = DataSourceService(DataSourceRepository(db))
    row = service.get_by_id(source_id)
    if row is None:
        raise ApiError(status_code=404, code="DATA_SOURCE_NOT_FOUND", message="Data source not found")
    return to_data_source_item(row)


@router.patch("/{source_id}", summary="Update data source")
def update_data_source(
    source_id: str,
    payload: DataSourceUpdateModel,
    db: Session = Depends(get_db),
) -> DataSourceListItemModel:
    if not payload.model_dump(exclude_none=True):
        raise ApiError(status_code=400, code="EMPTY_UPDATE_PAYLOAD", message="No fields to update")
    service = DataSourceService(DataSourceRepository(db))
    row = service.update(source_id, payload)
    if row is None:
        raise ApiError(status_code=404, code="DATA_SOURCE_NOT_FOUND", message="Data source not found")
    return to_data_source_item(row)


@router.delete("", summary="Batch delete data sources")
def delete_data_sources(payload: BatchDeleteRequest, db: Session = Depends(get_db)) -> BatchDeleteResponse:
    service = DataSourceService(DataSourceRepository(db))
    deleted_count = service.batch_delete(payload.ids)
    return BatchDeleteResponse(deleted_count=deleted_count)
