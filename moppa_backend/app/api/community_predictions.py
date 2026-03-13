from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.db.models import AppUserEntity, CommunityPredictionEntity
from app.db.session import get_db
from app.models.community_prediction_model import (
    CommunityPredictionCreateModel,
    CommunityPredictionItemModel,
    CommunityPredictionListResponse,
    CommunityPredictionUpdateModel,
)
from app.services.community_prediction_service import CommunityPredictionService

router = APIRouter(prefix="/community-predictions", tags=["community-predictions"])


def to_prediction_item(entity: CommunityPredictionEntity, username: str) -> CommunityPredictionItemModel:
    return CommunityPredictionItemModel(
        id=str(entity.id),
        question_id=str(entity.question_id),
        user_id=str(entity.user_id),
        username=username,
        prediction_content=entity.prediction_content,
        confidence=float(entity.confidence) if entity.confidence is not None else None,
        reasoning=entity.reasoning,
        created_at=entity.created_at.isoformat(),
        updated_at=entity.updated_at.isoformat(),
    )


@router.get("", summary="List community predictions by question")
def list_community_predictions(
    question_id: str = Query(..., min_length=1),
    db: Session = Depends(get_db),
    _: object = Depends(get_current_user),
) -> CommunityPredictionListResponse:
    service = CommunityPredictionService(db)
    rows = service.list_by_question(question_id)
    return CommunityPredictionListResponse(items=[to_prediction_item(entity, username) for entity, username in rows])


@router.post("", summary="Create or update my prediction")
def upsert_my_prediction(
    payload: CommunityPredictionCreateModel,
    db: Session = Depends(get_db),
    current_user: AppUserEntity = Depends(get_current_user),
) -> CommunityPredictionItemModel:
    service = CommunityPredictionService(db)
    entity = service.upsert_for_user(payload, current_user.id)
    return to_prediction_item(entity, current_user.username)


@router.patch("/{prediction_id}", summary="Update my prediction")
def update_my_prediction(
    prediction_id: str,
    payload: CommunityPredictionUpdateModel,
    db: Session = Depends(get_db),
    current_user: AppUserEntity = Depends(get_current_user),
) -> CommunityPredictionItemModel:
    service = CommunityPredictionService(db)
    entity = service.update_mine(prediction_id, payload, current_user.id)
    return to_prediction_item(entity, current_user.username)
