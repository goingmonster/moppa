from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core import ApiError
from app.db.models import SystemConfigEntity
from app.db.session import get_db
from app.models.task_config_model import (
    TaskConfigCreateModel,
    TaskConfigItemModel,
    TaskConfigPaginationResponse,
    TaskConfigPayloadModel,
    TaskConfigUpdateModel,
)
from app.services.task_config_service import TaskConfigService


router = APIRouter(prefix="/task-configs", tags=["task-configs"])


def to_item(entity: SystemConfigEntity) -> TaskConfigItemModel:
    task_type = entity.key.removeprefix("task.")
    return TaskConfigItemModel(
        task_type=task_type,
        key=entity.key,
        description=entity.description,
        config=TaskConfigPayloadModel.model_validate(entity.value),
        created_at=entity.created_at,
        updated_at=entity.updated_at,
    )


@router.post("", summary="Create task config")
def create_task_config(payload: TaskConfigCreateModel, db: Session = Depends(get_db)) -> TaskConfigItemModel:
    service = TaskConfigService(db)
    existed = service.get_by_task_type(payload.task_type)
    if existed is not None:
        raise ApiError(status_code=409, code="TASK_CONFIG_EXISTS", message="Task config already exists")
    return to_item(service.create(payload))


@router.get("", summary="List task configs")
def list_task_configs(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> TaskConfigPaginationResponse:
    service = TaskConfigService(db)
    rows, total = service.list_paginated(page=page, page_size=page_size)
    return TaskConfigPaginationResponse(page=page, page_size=page_size, total=total, items=[to_item(row) for row in rows])


@router.get("/{task_type}", summary="Get task config")
def get_task_config(task_type: str, db: Session = Depends(get_db)) -> TaskConfigItemModel:
    service = TaskConfigService(db)
    entity = service.get_by_task_type(task_type)
    if entity is None:
        raise ApiError(status_code=404, code="TASK_CONFIG_NOT_FOUND", message="Task config not found")
    return to_item(entity)


@router.patch("/{task_type}", summary="Update task config")
def update_task_config(task_type: str, payload: TaskConfigUpdateModel, db: Session = Depends(get_db)) -> TaskConfigItemModel:
    if payload.config is None and payload.description is None:
        raise ApiError(status_code=400, code="EMPTY_UPDATE_PAYLOAD", message="No fields to update")
    service = TaskConfigService(db)
    entity = service.update(task_type, payload)
    if entity is None:
        raise ApiError(status_code=404, code="TASK_CONFIG_NOT_FOUND", message="Task config not found")
    return to_item(entity)


@router.delete("/{task_type}", summary="Delete task config")
def delete_task_config(task_type: str, db: Session = Depends(get_db)) -> dict[str, bool]:
    service = TaskConfigService(db)
    deleted = service.delete(task_type)
    if not deleted:
        raise ApiError(status_code=404, code="TASK_CONFIG_NOT_FOUND", message="Task config not found")
    return {"deleted": True}
