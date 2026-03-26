from uuid import UUID

from sqlalchemy.orm import Session

from app.core import ApiError
from app.db.models import AgentPredictionEntity
from app.models.agent_prediction_model import (
    AgentPredictionItemModel,
    AgentPredictionSubmitModel,
    EvidenceItem,
)
from app.repositories.agent_prediction_repository import AgentPredictionRepository


class AgentPredictionService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repository = AgentPredictionRepository(db)

    def submit(self, payload: AgentPredictionSubmitModel, api_key_id: UUID) -> AgentPredictionEntity:
        question_id = self._parse_uuid(payload.id, "id")
        question = self.repository.get_question(question_id)
        if question is None:
            raise ApiError(status_code=404, code="QUESTION_NOT_FOUND", message="Question not found")

        evidence_data = [item.model_dump() for item in payload.evidence]
        entity = self.repository.upsert(
            question_id=question_id,
            api_key_id=api_key_id,
            model_name=payload.model_name.strip(),
            prediction_content=payload.answer.strip(),
            reasoning=payload.reason.strip() if payload.reason else None,
            confidence=payload.confidence,
            evidence=evidence_data,
            question_text=payload.question.strip(),
        )
        return entity

    def list_by_question(self, question_id: str) -> list[AgentPredictionItemModel]:
        uuid = self._parse_uuid(question_id, "question_id")
        rows = self.repository.list_by_question(uuid)
        return [self._to_item(entity, agent_name, user_type, purpose) for entity, agent_name, user_type, purpose, _ in rows]

    @staticmethod
    def _parse_uuid(value: str, field_name: str) -> UUID:
        try:
            return UUID(value)
        except ValueError as exc:
            raise ApiError(status_code=422, code=f"INVALID_{field_name.upper()}", message=f"Invalid {field_name}: {value}") from exc

    @staticmethod
    def _to_item(entity, agent_name: str, user_type: str, purpose: str | None) -> AgentPredictionItemModel:
        evidence_items = []
        if isinstance(entity.evidence, list):
            for item in entity.evidence:
                if isinstance(item, dict):
                    evidence_items.append(EvidenceItem(url=item.get("url", ""), content=item.get("content", "")))
        return AgentPredictionItemModel(
            id=str(entity.id),
            question_id=str(entity.question_id),
            api_key_id=str(entity.api_key_id),
            agent_name=agent_name,
            user_type=user_type,
            purpose=purpose,
            model_name=entity.model_name,
            prediction_content=entity.prediction_content,
            reasoning=entity.reasoning,
            confidence=entity.confidence,
            evidence=evidence_items,
            question_text=entity.question_text,
            status=entity.status,
            created_at=entity.created_at.isoformat(),
        )
