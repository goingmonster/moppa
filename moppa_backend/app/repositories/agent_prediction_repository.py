from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core import ApiError
from app.db.models import AgentPredictionEntity, ApiKeyEntity, QuestionEntity


class AgentPredictionRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_existing(self, question_id: UUID, api_key_id: UUID) -> AgentPredictionEntity | None:
        return self.db.scalar(
            select(AgentPredictionEntity).where(
                AgentPredictionEntity.question_id == question_id,
                AgentPredictionEntity.api_key_id == api_key_id,
                AgentPredictionEntity.deleted_at.is_(None),
            )
        )

    def upsert(self, question_id: UUID, api_key_id: UUID, model_name: str,
                prediction_content: str, reasoning: str | None, confidence: int | None,
                evidence: list[dict[str, str]], question_text: str) -> AgentPredictionEntity:
        existing = self.get_existing(question_id, api_key_id)
        if existing is not None:
            existing.model_name = model_name
            existing.prediction_content = prediction_content
            existing.reasoning = reasoning
            existing.confidence = confidence
            existing.evidence = evidence
            existing.question_text = question_text
            existing.status = "completed"
            existing.updated_at = datetime.now(timezone.utc)
            self.db.commit()
            self.db.refresh(existing)
            return existing

        entity = AgentPredictionEntity(
            question_id=question_id,
            api_key_id=api_key_id,
            model_name=model_name,
            prediction_content=prediction_content,
            reasoning=reasoning,
            confidence=confidence,
            evidence=evidence,
            question_text=question_text,
            status="completed",
        )
        self.db.add(entity)
        self.db.commit()
        self.db.refresh(entity)
        return entity

    def list_by_question(self, question_id: UUID) -> list[tuple[AgentPredictionEntity, str, str, str | None, str]]:
        rows = self.db.execute(
            select(
                AgentPredictionEntity,
                ApiKeyEntity.name,
                ApiKeyEntity.user_type,
                ApiKeyEntity.purpose,
                ApiKeyEntity.id,
            )
            .join(ApiKeyEntity, ApiKeyEntity.id == AgentPredictionEntity.api_key_id)
            .where(
                AgentPredictionEntity.question_id == question_id,
                AgentPredictionEntity.deleted_at.is_(None),
            )
            .order_by(AgentPredictionEntity.created_at.desc())
        ).all()
        return [(row[0], row[1], row[2], row[3], str(row[4])) for row in rows]

    def get_question(self, question_id: UUID) -> QuestionEntity | None:
        entity = self.db.get(QuestionEntity, question_id)
        if entity is None or entity.deleted_at is not None:
            return None
        return entity
