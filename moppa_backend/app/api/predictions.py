from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.dependencies import require_admin_user
from app.db.session import get_db
from app.models.prediction_model import PredictionItemModel
from app.services.model_prediction_service import ModelPredictionService

router = APIRouter(tags=["predictions"])


@router.post("/jobs/model-prediction-now", summary="Trigger model prediction job now")
def trigger_model_prediction_now(
    db: Session = Depends(get_db),
    _: object = Depends(require_admin_user),
) -> dict[str, str]:
    service = ModelPredictionService(db)
    result = service.run_prediction_job(force_run=True)
    return {"task_id": result.task_id, "status": result.status}


@router.get("/predictions/question/{question_id}", summary="List model predictions for a question")
def list_model_predictions(
    question_id: str,
    db: Session = Depends(get_db),
) -> list[PredictionItemModel]:
    service = ModelPredictionService(db)
    return service.list_by_question(question_id)
