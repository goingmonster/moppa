from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core import ApiError
from app.api.dependencies import get_current_user, require_admin_user
from app.db.models import QuestionEntity
from app.db.session import get_db
from app.models.common_model import BatchDeleteResponse
from app.models.question_model import (
    QuestionBatchDeleteRequest,
    QuestionCreateModel,
    QuestionListItemModel,
    QuestionPaginationResponse,
    QuestionUpdateModel,
)
from app.services.question_service import QuestionService

router = APIRouter(prefix="/questions", tags=["questions"])


def to_question_list_item(entity: QuestionEntity, event_ids: list[str] | None = None) -> QuestionListItemModel:
    resolved_event_ids = event_ids if event_ids is not None else ([str(entity.event_id)] if entity.event_id else [])
    return QuestionListItemModel(
        id=str(entity.id),
        event_id=str(entity.event_id) if entity.event_id else None,
        event_ids=resolved_event_ids,
        template_id=str(entity.template_id) if entity.template_id else None,
        level=entity.level,
        content=entity.content,
        match_score=entity.match_score,
        event_domain=entity.event_domain,
        event_type=entity.event_type,
        area=entity.area,
        input_type=entity.input_type,
        background=entity.background,
        answer_space=entity.answer_space,
        verification_conditions=entity.verification_conditions,
        deadline=entity.deadline.isoformat(),
        status=entity.status,
        trace_id=str(entity.trace_id),
        delete_reason=entity.delete_reason,
        deleted_at=entity.deleted_at.isoformat() if entity.deleted_at is not None else None,
    )


@router.post("", summary="Create question")
def create_question(
    payload: QuestionCreateModel,
    db: Session = Depends(get_db),
    _: object = Depends(require_admin_user),
) -> dict[str, str]:
    service = QuestionService(db)
    try:
        question_id = service.create(payload)
    except ValueError as exc:
        raise ApiError(status_code=422, code="INVALID_EVENT_IDS", message=str(exc)) from exc
    return {"id": question_id}


@router.get("", summary="List questions")
def list_questions(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1),
    event_domain: str = Query(default=""),
    event_type: str = Query(default=""),
    status: str = Query(default=""),
    level: int | None = Query(default=None, ge=1, le=4),
    deadline_from: datetime | None = Query(default=None),
    deadline_to: datetime | None = Query(default=None),
    deleted_mode: str = Query(default="active_only"),
    include_deleted: bool | None = Query(default=None),
    db: Session = Depends(get_db),
    _: object = Depends(get_current_user),
) -> QuestionPaginationResponse:
    service = QuestionService(db)
    resolved_deleted_mode = deleted_mode
    if include_deleted is not None:
        resolved_deleted_mode = "with_deleted" if include_deleted else "active_only"
    try:
        rows, total = service.list_paginated(
            page=page,
            page_size=page_size,
            event_domain=event_domain,
            event_type=event_type,
            status=status,
            level=level,
            deadline_from=deadline_from,
            deadline_to=deadline_to,
            deleted_mode=resolved_deleted_mode,
        )
    except ValueError as exc:
        message = str(exc)
        if message.startswith("invalid question status"):
            raise ApiError(status_code=422, code="INVALID_QUESTION_STATUS", message=message) from exc
        if message.startswith("invalid deleted mode"):
            raise ApiError(status_code=422, code="INVALID_DELETED_MODE", message=message) from exc
        raise
    event_map = service.get_event_ids_map([str(row.id) for row in rows])
    items = [
        to_question_list_item(
            row,
            event_map.get(str(row.id), [str(row.event_id)] if row.event_id else []),
        )
        for row in rows
    ]
    return QuestionPaginationResponse(page=page, page_size=page_size, total=total, items=items)


@router.get("/search", summary="Search questions by content")
def search_questions(
    keyword: str = Query(default=""),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1),
    event_domain: str = Query(default=""),
    event_type: str = Query(default=""),
    status: str = Query(default=""),
    level: int | None = Query(default=None, ge=1, le=4),
    deadline_from: datetime | None = Query(default=None),
    deadline_to: datetime | None = Query(default=None),
    deleted_mode: str = Query(default="active_only"),
    include_deleted: bool | None = Query(default=None),
    db: Session = Depends(get_db),
    _: object = Depends(get_current_user),
) -> QuestionPaginationResponse:
    service = QuestionService(db)
    resolved_deleted_mode = deleted_mode
    if include_deleted is not None:
        resolved_deleted_mode = "with_deleted" if include_deleted else "active_only"
    try:
        rows, total = service.search_paginated(
            keyword=keyword,
            page=page,
            page_size=page_size,
            event_domain=event_domain,
            event_type=event_type,
            status=status,
            level=level,
            deadline_from=deadline_from,
            deadline_to=deadline_to,
            deleted_mode=resolved_deleted_mode,
        )
    except ValueError as exc:
        message = str(exc)
        if message.startswith("invalid question status"):
            raise ApiError(status_code=422, code="INVALID_QUESTION_STATUS", message=message) from exc
        if message.startswith("invalid deleted mode"):
            raise ApiError(status_code=422, code="INVALID_DELETED_MODE", message=message) from exc
        raise
    event_map = service.get_event_ids_map([str(row.id) for row in rows])
    items = [
        to_question_list_item(
            row,
            event_map.get(str(row.id), [str(row.event_id)] if row.event_id else []),
        )
        for row in rows
    ]
    return QuestionPaginationResponse(page=page, page_size=page_size, total=total, items=items)


@router.delete("", summary="Batch delete questions")
def delete_questions(
    payload: QuestionBatchDeleteRequest,
    db: Session = Depends(get_db),
    _: object = Depends(require_admin_user),
) -> BatchDeleteResponse:
    service = QuestionService(db)
    deleted_count = service.batch_delete(payload.ids, payload.delete_reason)
    return BatchDeleteResponse(deleted_count=deleted_count)


@router.get("/{question_id}", summary="Get question detail")
def get_question(
    question_id: str,
    db: Session = Depends(get_db),
    _: object = Depends(get_current_user),
) -> QuestionListItemModel:
    service = QuestionService(db)
    entity = service.get_by_id(question_id)
    if entity is None:
        raise ApiError(status_code=404, code="QUESTION_NOT_FOUND", message="Question not found")
    event_ids = service.get_event_ids(question_id)
    return to_question_list_item(entity, event_ids if event_ids else ([str(entity.event_id)] if entity.event_id else []))


@router.patch("/{question_id}", summary="Update question")
def update_question(
    question_id: str,
    payload: QuestionUpdateModel,
    db: Session = Depends(get_db),
    _: object = Depends(require_admin_user),
) -> QuestionListItemModel:
    service = QuestionService(db)
    if not payload.model_dump(exclude_none=True):
        raise ApiError(status_code=400, code="EMPTY_UPDATE_PAYLOAD", message="No fields to update")
    try:
        entity = service.update(question_id, payload)
    except ValueError as exc:
        message = str(exc)
        if message.startswith("invalid question status"):
            raise ApiError(status_code=422, code="INVALID_QUESTION_STATUS", message=message) from exc
        raise ApiError(status_code=422, code="INVALID_EVENT_IDS", message=message) from exc
    if entity is None:
        raise ApiError(status_code=404, code="QUESTION_NOT_FOUND", message="Question not found")
    event_ids = service.get_event_ids(question_id)
    return to_question_list_item(entity, event_ids if event_ids else ([str(entity.event_id)] if entity.event_id else []))
