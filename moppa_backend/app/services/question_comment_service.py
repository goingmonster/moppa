from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from app.core import ApiError
from app.db.models import FeedbackEntity
from app.models.question_comment_model import QuestionCommentCreateModel, QuestionCommentUpdateModel
from app.repositories.question_comment_repository import QuestionCommentRepository
from app.repositories.question_repository import QuestionRepository


class QuestionCommentService:
    def __init__(self, db: Session) -> None:
        self.repository = QuestionCommentRepository(db)
        self.question_repository = QuestionRepository(db)

    def list_by_question(self, question_id: str) -> list[tuple[FeedbackEntity, str]]:
        question_uuid = self._parse_uuid(question_id, "question_id")
        return self.repository.list_by_question(question_uuid)

    def get_stats_by_questions(self, question_ids: list[str], user_id: UUID) -> tuple[dict[str, int], dict[str, int]]:
        question_uuid_ids = self._parse_uuid_list(question_ids, "question_ids")
        return self.repository.get_stats_by_questions(question_uuid_ids, user_id)

    def create_for_user(self, payload: QuestionCommentCreateModel, user_id: UUID) -> FeedbackEntity:
        question_uuid = self._parse_uuid(payload.question_id, "question_id")
        question = self.question_repository.get_by_id(str(question_uuid))
        if question is None:
            raise ApiError(status_code=404, code="QUESTION_NOT_FOUND", message="Question not found")
        self._validate_question_open(question.status, question.deadline)

        content = payload.content.strip()
        if not content:
            raise ApiError(status_code=422, code="INVALID_COMMENT_CONTENT", message="Comment content cannot be empty")

        return self.repository.create(
            question_id=question_uuid,
            user_id=user_id,
            content=content,
            trace_id=uuid4(),
        )

    def update_mine(self, comment_id: str, payload: QuestionCommentUpdateModel, user_id: UUID) -> FeedbackEntity:
        comment_uuid = self._parse_uuid(comment_id, "comment_id")
        entity = self.repository.get_by_id(comment_uuid)
        if entity is None:
            raise ApiError(status_code=404, code="COMMENT_NOT_FOUND", message="Comment not found")
        if entity.user_id != user_id:
            raise ApiError(status_code=403, code="FORBIDDEN", message="You can only edit your own comment")

        content = payload.content.strip()
        if not content:
            raise ApiError(status_code=422, code="INVALID_COMMENT_CONTENT", message="Comment content cannot be empty")

        return self.repository.update_content(entity, content)

    def delete_comment(self, comment_id: str, user_id: UUID, user_role: str) -> None:
        comment_uuid = self._parse_uuid(comment_id, "comment_id")
        entity = self.repository.get_by_id(comment_uuid)
        if entity is None:
            raise ApiError(status_code=404, code="COMMENT_NOT_FOUND", message="Comment not found")

        if entity.user_id != user_id and user_role != "admin":
            raise ApiError(status_code=403, code="FORBIDDEN", message="You can only delete your own comment")

        self.repository.soft_delete(entity)

    @staticmethod
    def _validate_question_open(status: str, deadline: datetime) -> None:
        normalized = status.strip()
        if normalized not in {"draft", "collecting"}:
            raise ApiError(status_code=409, code="QUESTION_NOT_COLLECTING", message="Question is not collecting comments")

        now = datetime.now(timezone.utc)
        effective_deadline = deadline if deadline.tzinfo is not None else deadline.replace(tzinfo=timezone.utc)
        if effective_deadline <= now:
            raise ApiError(status_code=409, code="QUESTION_DEADLINE_PASSED", message="Question deadline has passed")

    @staticmethod
    def _parse_uuid(raw: str, field_name: str) -> UUID:
        try:
            return UUID(raw)
        except ValueError as exc:
            raise ApiError(
                status_code=422,
                code="INVALID_UUID",
                message=f"{field_name} must be UUID",
                details={"field": field_name, "value": raw},
            ) from exc

    @classmethod
    def _parse_uuid_list(cls, raws: list[str], field_name: str) -> list[UUID]:
        return [cls._parse_uuid(raw, field_name) for raw in raws]
