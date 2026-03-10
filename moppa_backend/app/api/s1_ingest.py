from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.s1_ingest_model import S1PullNowRequestModel, S1PushRequestModel, S1TaskResponseModel
from app.services.s1_ingest_service import S1IngestService


router = APIRouter(prefix="/s1", tags=["s1-ingest"])


@router.post("/events/push", summary="Push events into S1 pool")
def push_events(payload: S1PushRequestModel, db: Session = Depends(get_db)) -> S1TaskResponseModel:
    service = S1IngestService(db)
    return service.run_push_job(payload)


@router.post("/jobs/pull-now", summary="Trigger S1 pull job now")
def pull_now(payload: S1PullNowRequestModel, db: Session = Depends(get_db)) -> S1TaskResponseModel:
    service = S1IngestService(db)
    return service.run_pull_job(payload)
