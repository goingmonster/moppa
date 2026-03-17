from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core import ApiError
from app.api.dependencies import require_admin_user
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


router = APIRouter(prefix="/question-templates", tags=["question-templates"], dependencies=[Depends(require_admin_user)])


def to_item(entity: QuestionTemplateEntity) -> QuestionTemplateListItemModel:
    return QuestionTemplateListItemModel(
        id=str(entity.id),
        template_index=entity.template_index,
        question_template=entity.question_template,
        difficulty_level=entity.difficulty_level,
        candidate_answer_type=entity.candidate_answer_type,
        event_domain=entity.event_domain,
        event_type=entity.event_type,
        event_type_id=entity.event_type_id,
        operation_level=entity.operation_level,
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
    page_size: int = Query(default=20, ge=1),
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
