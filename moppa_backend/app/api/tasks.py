from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core import ApiError
from app.db.models import TaskExecutionEntity
from app.db.session import get_db
from app.models.common_model import BatchDeleteRequest, BatchDeleteResponse
from app.models.task_execution_model import (
    TaskExecutionCreateModel,
    TaskExecutionListItemModel,
    TaskExecutionPaginationResponse,
    TaskExecutionUpdateModel,
    TaskExecutionStatusUpdateModel,
)
from app.services.task_execution_service import TaskExecutionService

router = APIRouter(prefix="/tasks", tags=["tasks"])


def to_task_list_item(entity: TaskExecutionEntity) -> TaskExecutionListItemModel:
    return TaskExecutionListItemModel(
        id=str(entity.id),
        task_type=entity.task_type,
        idempotency_key=entity.idempotency_key,
        status=entity.status,
        attempt_count=entity.attempt_count,
        trace_id=str(entity.trace_id),
    )


@router.post("", summary="Create task execution")
def create_task(payload: TaskExecutionCreateModel, db: Session = Depends(get_db)) -> dict[str, str]:
    service = TaskExecutionService(db)
    task_id = service.create(payload)
    return {"id": task_id}


@router.get("", summary="List task executions")
def list_tasks(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> TaskExecutionPaginationResponse:
    service = TaskExecutionService(db)
    rows, total = service.list_paginated(page=page, page_size=page_size)
    items = [to_task_list_item(row) for row in rows]
    return TaskExecutionPaginationResponse(page=page, page_size=page_size, total=total, items=items)


@router.patch("/{task_id}/status", summary="Update task status")
def update_task_status(task_id: str, payload: TaskExecutionStatusUpdateModel, db: Session = Depends(get_db)) -> dict[str, str]:
    service = TaskExecutionService(db)
    updated = service.update_status(task_id=task_id, status=payload.status)
    if not updated:
        raise ApiError(status_code=404, code="TASK_NOT_FOUND", message="Task not found")
    return {"status": "updated"}


@router.get("/{task_id}", summary="Get task execution detail")
def get_task(task_id: str, db: Session = Depends(get_db)) -> TaskExecutionListItemModel:
    service = TaskExecutionService(db)
    entity = service.get_by_id(task_id)
    if entity is None:
        raise ApiError(status_code=404, code="TASK_NOT_FOUND", message="Task not found")
    return to_task_list_item(entity)


@router.patch("/{task_id}", summary="Update task execution")
def update_task(task_id: str, payload: TaskExecutionUpdateModel, db: Session = Depends(get_db)) -> TaskExecutionListItemModel:
    service = TaskExecutionService(db)
    if not payload.model_dump(exclude_none=True):
        raise ApiError(status_code=400, code="EMPTY_UPDATE_PAYLOAD", message="No fields to update")
    entity = service.update(task_id, payload)
    if entity is None:
        raise ApiError(status_code=404, code="TASK_NOT_FOUND", message="Task not found")
    return to_task_list_item(entity)


@router.delete("", summary="Batch delete task executions")
def delete_tasks(payload: BatchDeleteRequest, db: Session = Depends(get_db)) -> BatchDeleteResponse:
    service = TaskExecutionService(db)
    deleted_count = service.batch_delete(payload.ids)
    return BatchDeleteResponse(deleted_count=deleted_count)
