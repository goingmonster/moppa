from datetime import timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core import ApiError
from app.db.models import QuestionTemplateEntity
from app.db.session import get_db
from app.models.common_model import BatchDeleteRequest, BatchDeleteResponse
from app.models.question_template_model import (
    QuestionTemplateCreateModel,
    QuestionTemplateListItemModel,
    QuestionTemplatePaginationResponse,
    QuestionTemplateUpdateModel,
)
from app.services.question_template_service import QuestionTemplateService


router = APIRouter(prefix="/question-templates", tags=["question-templates"])


def _interval_to_text(value: timedelta) -> str:
    total_seconds = int(value.total_seconds())
    if total_seconds % 86400 == 0:
        days = total_seconds // 86400
        return f"{days} day" if days == 1 else f"{days} days"
    if total_seconds % 3600 == 0:
        hours = total_seconds // 3600
        return f"{hours} hour" if hours == 1 else f"{hours} hours"
    minutes = max(total_seconds // 60, 1)
    return f"{minutes} minute" if minutes == 1 else f"{minutes} minutes"


def to_item(entity: QuestionTemplateEntity) -> QuestionTemplateListItemModel:
    return QuestionTemplateListItemModel(
        id=str(entity.id),
        name=entity.name,
        level=entity.level,
        category=entity.category,
        template_content=entity.template_content,
        variables=entity.variables,
        generation_config=entity.generation_config,
        verification_conditions=entity.verification_conditions,
        duplicate_check_window=_interval_to_text(entity.duplicate_check_window),
        max_duplicate_rate=float(entity.max_duplicate_rate),
        status=entity.status,
        version=entity.version,
        usage_count=entity.usage_count,
        created_at=entity.created_at,
        updated_at=entity.updated_at,
    )


@router.post("", summary="Create question template")
def create_question_template(
    payload: QuestionTemplateCreateModel,
    db: Session = Depends(get_db),
) -> QuestionTemplateListItemModel:
    service = QuestionTemplateService(db)
    entity = service.create(payload)
    return to_item(entity)


@router.get("", summary="List question templates")
def list_question_templates(
    keyword: str = Query(default=""),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    get_all: bool = Query(default=False),
    db: Session = Depends(get_db),
) -> QuestionTemplatePaginationResponse:
    service = QuestionTemplateService(db)
    if get_all:
        rows = service.list_all(keyword=keyword)
        items = [to_item(row) for row in rows]
        return QuestionTemplatePaginationResponse(page=1, page_size=len(items), total=len(items), items=items)

    if keyword.strip():
        rows, total = service.search_paginated(keyword=keyword, page=page, page_size=page_size)
    else:
        rows, total = service.list_paginated(page=page, page_size=page_size)
    items = [to_item(row) for row in rows]
    return QuestionTemplatePaginationResponse(page=page, page_size=page_size, total=total, items=items)


@router.get("/{template_id}", summary="Get question template detail")
def get_question_template(template_id: str, db: Session = Depends(get_db)) -> QuestionTemplateListItemModel:
    service = QuestionTemplateService(db)
    entity = service.get_by_id(template_id)
    if entity is None:
        raise ApiError(status_code=404, code="QUESTION_TEMPLATE_NOT_FOUND", message="Question template not found")
    return to_item(entity)


@router.patch("/{template_id}", summary="Update question template")
def update_question_template(
    template_id: str,
    payload: QuestionTemplateUpdateModel,
    db: Session = Depends(get_db),
) -> QuestionTemplateListItemModel:
    if not payload.model_dump(exclude_none=True):
        raise ApiError(status_code=400, code="EMPTY_UPDATE_PAYLOAD", message="No fields to update")
    service = QuestionTemplateService(db)
    entity = service.update(template_id, payload)
    if entity is None:
        raise ApiError(status_code=404, code="QUESTION_TEMPLATE_NOT_FOUND", message="Question template not found")
    return to_item(entity)


@router.delete("", summary="Batch delete question templates")
def delete_question_templates(payload: BatchDeleteRequest, db: Session = Depends(get_db)) -> BatchDeleteResponse:
    service = QuestionTemplateService(db)
    deleted_count = service.batch_delete(payload.ids)
    return BatchDeleteResponse(deleted_count=deleted_count)
