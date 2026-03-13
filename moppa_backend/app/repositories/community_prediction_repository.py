from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import AppUserEntity, CommunityPredictionEntity


class CommunityPredictionRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_by_question(self, question_id: UUID) -> list[tuple[CommunityPredictionEntity, str]]:
        rows = list(
            self.db.execute(
                select(CommunityPredictionEntity, AppUserEntity.username)
                .join(AppUserEntity, AppUserEntity.id == CommunityPredictionEntity.user_id)
                .where(
                    CommunityPredictionEntity.question_id == question_id,
                    CommunityPredictionEntity.deleted_at.is_(None),
                    AppUserEntity.deleted_at.is_(None),
                )
                .order_by(CommunityPredictionEntity.created_at.desc())
            )
        )
        return [(entity, username) for entity, username in rows]

    def get_by_question_user(self, question_id: UUID, user_id: UUID) -> CommunityPredictionEntity | None:
        return self.db.scalar(
            select(CommunityPredictionEntity).where(
                CommunityPredictionEntity.question_id == question_id,
                CommunityPredictionEntity.user_id == user_id,
                CommunityPredictionEntity.deleted_at.is_(None),
            )
        )

    def get_by_id(self, prediction_id: UUID) -> CommunityPredictionEntity | None:
        entity = self.db.get(CommunityPredictionEntity, prediction_id)
        if entity is None or entity.deleted_at is not None:
            return None
        return entity

    def create(
        self,
        question_id: UUID,
        user_id: UUID,
        prediction_content: str,
        confidence: float | None,
        reasoning: str | None,
        trace_id: UUID,
    ) -> CommunityPredictionEntity:
        entity = CommunityPredictionEntity(
            question_id=question_id,
            user_id=user_id,
            prediction_content=prediction_content,
            confidence=confidence,
            reasoning=reasoning,
            trace_id=trace_id,
        )
        self.db.add(entity)
        self.db.commit()
        self.db.refresh(entity)
        return entity

    def update(
        self,
        entity: CommunityPredictionEntity,
        prediction_content: str,
        confidence: float | None,
        reasoning: str | None,
    ) -> CommunityPredictionEntity:
        entity.prediction_content = prediction_content
        entity.confidence = confidence
        entity.reasoning = reasoning
        entity.updated_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(entity)
        return entity
