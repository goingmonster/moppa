from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.db.models import AppUserEntity, FeedbackEntity
from app.db.session import get_db
from app.models.question_comment_model import (
    QuestionCommentCreateModel,
    QuestionCommentItemModel,
    QuestionCommentListResponse,
    QuestionCommentUpdateModel,
)
from app.services.question_comment_service import QuestionCommentService

router = APIRouter(prefix="/question-comments", tags=["question-comments"])


def to_comment_item(entity: FeedbackEntity, username: str) -> QuestionCommentItemModel:
    return QuestionCommentItemModel(
        id=str(entity.id),
        question_id=str(entity.target_id),
        user_id=str(entity.user_id),
        username=username,
        content=entity.content,
        created_at=entity.created_at.isoformat(),
        updated_at=entity.updated_at.isoformat(),
    )


@router.get("", summary="List question comments")
def list_question_comments(
    question_id: str = Query(..., min_length=1),
    db: Session = Depends(get_db),
    _: object = Depends(get_current_user),
) -> QuestionCommentListResponse:
    service = QuestionCommentService(db)
    rows = service.list_by_question(question_id)
    return QuestionCommentListResponse(items=[to_comment_item(entity, username) for entity, username in rows])


@router.post("", summary="Create question comment")
def create_question_comment(
    payload: QuestionCommentCreateModel,
    db: Session = Depends(get_db),
    current_user: AppUserEntity = Depends(get_current_user),
) -> QuestionCommentItemModel:
    service = QuestionCommentService(db)
    entity = service.create_for_user(payload, current_user.id)
    return to_comment_item(entity, current_user.username)


@router.patch("/{comment_id}", summary="Update my question comment")
def update_question_comment(
    comment_id: str,
    payload: QuestionCommentUpdateModel,
    db: Session = Depends(get_db),
    current_user: AppUserEntity = Depends(get_current_user),
) -> QuestionCommentItemModel:
    service = QuestionCommentService(db)
    entity = service.update_mine(comment_id, payload, current_user.id)
    return to_comment_item(entity, current_user.username)
