from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from app.core import ApiError
from app.db.models import CommunityPredictionEntity
from app.models.community_prediction_model import CommunityPredictionCreateModel, CommunityPredictionUpdateModel
from app.repositories.community_prediction_repository import CommunityPredictionRepository
from app.repositories.question_repository import QuestionRepository


class CommunityPredictionService:
    def __init__(self, db: Session) -> None:
        self.repository = CommunityPredictionRepository(db)
        self.question_repository = QuestionRepository(db)

    def list_by_question(self, question_id: str) -> list[tuple[CommunityPredictionEntity, str]]:
        question_uuid = self._parse_uuid(question_id, "question_id")
        return self.repository.list_by_question(question_uuid)

    def get_stats_by_questions(self, question_ids: list[str], user_id: UUID) -> tuple[dict[str, int], set[str]]:
        question_uuid_ids = self._parse_uuid_list(question_ids, "question_ids")
        return self.repository.get_stats_by_questions(question_uuid_ids, user_id)

    def upsert_for_user(self, payload: CommunityPredictionCreateModel, user_id: UUID) -> CommunityPredictionEntity:
        question_uuid = self._parse_uuid(payload.question_id, "question_id")
        question = self.question_repository.get_by_id(str(question_uuid))
        if question is None:
            raise ApiError(status_code=404, code="QUESTION_NOT_FOUND", message="Question not found")
        self._validate_question_open(question.status)

        prediction_content = payload.prediction_content.strip()
        if not prediction_content:
            raise ApiError(status_code=422, code="INVALID_PREDICTION_CONTENT", message="Prediction content cannot be empty")
        reasoning = payload.reasoning.strip() if payload.reasoning is not None else None

        # 先查找未删除的预测
        existing = self.repository.get_by_question_user(question_uuid, user_id)
        if existing is not None:
            return self.repository.update(
                existing,
                prediction_content=prediction_content,
                confidence=payload.confidence,
                reasoning=reasoning,
            )

        # 再查找已删除的预测（用于恢复）
        deleted = self.repository.get_by_question_user_including_deleted(question_uuid, user_id)
        if deleted is not None:
            from datetime import datetime, timezone
            deleted.prediction_content = prediction_content
            deleted.confidence = payload.confidence
            deleted.reasoning = reasoning
            deleted.deleted_at = None  # 恢复预测
            deleted.updated_at = datetime.now(timezone.utc)
            self.repository.db.commit()
            self.repository.db.refresh(deleted)
            return deleted

        # 创建新预测
        return self.repository.create(
            question_id=question_uuid,
            user_id=user_id,
            prediction_content=prediction_content,
            confidence=payload.confidence,
            reasoning=reasoning,
            trace_id=uuid4(),
        )

    def update_mine(self, prediction_id: str, payload: CommunityPredictionUpdateModel, user_id: UUID) -> CommunityPredictionEntity:
        prediction_uuid = self._parse_uuid(prediction_id, "prediction_id")
        entity = self.repository.get_by_id(prediction_uuid)
        if entity is None:
            raise ApiError(status_code=404, code="PREDICTION_NOT_FOUND", message="Prediction not found")
        if entity.user_id != user_id:
            raise ApiError(status_code=403, code="FORBIDDEN", message="You can only edit your own prediction")

        question = self.question_repository.get_by_id(str(entity.question_id))
        if question is None:
            raise ApiError(status_code=404, code="QUESTION_NOT_FOUND", message="Question not found")
        self._validate_question_open(question.status)

        next_content = payload.prediction_content.strip() if payload.prediction_content is not None else entity.prediction_content
        if not next_content:
            raise ApiError(status_code=422, code="INVALID_PREDICTION_CONTENT", message="Prediction content cannot be empty")
        next_reasoning = payload.reasoning.strip() if payload.reasoning is not None else entity.reasoning
        next_confidence = payload.confidence if payload.confidence is not None else entity.confidence

        return self.repository.update(
            entity,
            prediction_content=next_content,
            confidence=next_confidence,
            reasoning=next_reasoning,
        )

    @staticmethod
    def _validate_question_open(status: str) -> None:
        normalized = status.strip().lower()
        if normalized == "expired":
            raise ApiError(status_code=409, code="QUESTION_EXPIRED", message="Expired question does not accept predictions")

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

    def delete_for_user(self, prediction_id: str, user_id: UUID) -> CommunityPredictionEntity:
        prediction_uuid = self._parse_uuid(prediction_id, "prediction_id")
        entity = self.repository.get_by_id(prediction_uuid)
        if entity is None:
            raise ApiError(status_code=404, code="PREDICTION_NOT_FOUND", message="Prediction not found")
        if entity.user_id != user_id:
            raise ApiError(status_code=403, code="FORBIDDEN", message="You can only delete your own prediction")

        question = self.question_repository.get_by_id(str(entity.question_id))
        if question is None:
            raise ApiError(status_code=404, code="QUESTION_NOT_FOUND", message="Question not found")
        self._validate_question_open(question.status)

        return self.repository.delete_for_user(prediction_uuid, user_id)
