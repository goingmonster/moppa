from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core import ApiError
from app.api.dependencies import require_admin_user
from app.db.session import get_db
from app.models.s1_ingest_model import (
    S1DryRunRequestModel,
    S1DryRunResponseModel,
    S1JobDetailResponseModel,
    S1PullNowRequestModel,
    S1PushRequestModel,
    S1TaskResponseModel,
)
from app.services.s1_auto_review_service import S1AutoReviewService
from app.services.auto_question_service import AutoQuestionService
from app.services.s1_ingest_service import S1IngestService


router = APIRouter(prefix="/s1", tags=["s1-ingest"], dependencies=[Depends(require_admin_user)])


@router.post("/events/push", summary="Push events into S1 pool")
def push_events(payload: S1PushRequestModel, db: Session = Depends(get_db)) -> S1TaskResponseModel:
    service = S1IngestService(db)
    return service.run_push_job(payload)


@router.post("/jobs/pull-now", summary="Trigger S1 pull job now")
def pull_now(payload: S1PullNowRequestModel, db: Session = Depends(get_db)) -> S1TaskResponseModel:
    service = S1IngestService(db)
    return service.run_pull_job(payload)


@router.post("/jobs/auto-review-now", summary="Trigger S1 auto review job now")
def auto_review_now(db: Session = Depends(get_db)) -> S1TaskResponseModel:
    service = S1AutoReviewService(db)
    return service.run_review_job(force_run=True)


@router.post("/jobs/auto-question-now", summary="Trigger auto question job now")
def auto_question_now(db: Session = Depends(get_db)) -> S1TaskResponseModel:
    service = AutoQuestionService(db)
    return service.run_auto_question_job(force_run=True)


@router.get("/jobs/{task_id}", summary="Get S1 job detail")
def get_job(task_id: str, db: Session = Depends(get_db)) -> S1JobDetailResponseModel:
    service = S1IngestService(db)
    detail = service.get_job_detail(task_id)
    if detail is None:
        raise ApiError(status_code=404, code="TASK_NOT_FOUND", message="Task not found")
    return detail


@router.post("/events/dry-run", summary="Dry-run S1 filtering for one event")
def dry_run_event(payload: S1DryRunRequestModel, db: Session = Depends(get_db)) -> S1DryRunResponseModel:
    service = S1IngestService(db)
    return service.dry_run_event(payload.event)
