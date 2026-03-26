from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_api_key, require_admin_user
from app.db.models import ApiKeyEntity, AppUserEntity
from app.db.session import get_db
from app.models.agent_prediction_model import (
    AgentPredictionItemModel,
    AgentPredictionSubmitModel,
)
from app.services.agent_prediction_service import AgentPredictionService

router = APIRouter(prefix="/agent-predictions", tags=["agent-predictions"])


@router.post("/submit", summary="Submit agent prediction")
def submit_prediction(
    payload: AgentPredictionSubmitModel,
    api_key: ApiKeyEntity = Depends(get_current_api_key),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    service = AgentPredictionService(db)
    entity = service.submit(payload, api_key_id=api_key.id)
    return {"id": str(entity.id), "status": entity.status}


@router.get("/question/{question_id}", summary="List agent predictions for a question")
def list_predictions(
    question_id: str,
    _user: AppUserEntity = Depends(require_admin_user),
    db: Session = Depends(get_db),
) -> list[AgentPredictionItemModel]:
    service = AgentPredictionService(db)
    return service.list_by_question(question_id)
