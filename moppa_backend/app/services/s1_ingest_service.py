import hashlib
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy.orm import Session

from app.db.models import TaskExecutionEntity
from app.models.s1_ingest_model import S1EventInputModel, S1PullNowRequestModel, S1PushRequestModel, S1TaskResponseModel
from app.repositories.data_source_repository import DataSourceRepository
from app.repositories.event_repository import EventRepository
from app.repositories.task_execution_repository import TaskExecutionRepository


class S1IngestService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.event_repository = EventRepository(db)
        self.data_source_repository = DataSourceRepository(db)
        self.task_repository = TaskExecutionRepository(db)

    def run_push_job(self, payload: S1PushRequestModel) -> S1TaskResponseModel:
        date_window = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
        idempotency_key = self._build_push_idempotency_key(payload.events, date_window)
        existing = self.task_repository.get_by_idempotency_key(idempotency_key)
        if existing is not None and existing.status in {"running", "completed"}:
            return self._to_task_response(existing)

        task = existing or self.task_repository.create_pending(
            task_type="s1_ingest_push",
            idempotency_key=idempotency_key,
            trace_id=uuid4(),
            business_id=None,
            date_window=date_window,
        )
        _ = self.task_repository.mark_running(task.id)

        accepted = 0
        duplicate = 0
        filtered = 0
        skipped = 0

        try:
            for item in payload.events:
                if not self.data_source_repository.exists_active_source_system(item.source_system):
                    skipped += 1
                    continue

                entity, created = self.event_repository.ingest_event(
                    event_key=item.event_key,
                    content=item.content,
                    source_system=item.source_system,
                    credibility_level=item.credibility_level,
                    event_time=item.event_time,
                    trace_id=item.trace_id,
                )

                if not created:
                    duplicate += 1
                    continue

                accepted += 1
                if item.credibility_level >= 3:
                    _ = self.event_repository.set_filter_result(entity.id, status="passed", reasons=["PASS_BASELINE"])
                else:
                    _ = self.event_repository.set_filter_result(entity.id, status="filtered", reasons=["FILTER_LOW_CREDIBILITY"])
                    filtered += 1

            result = {
                "accepted": accepted,
                "duplicate": duplicate,
                "filtered": filtered,
                "skipped_invalid_source": skipped,
            }
            metrics = {
                "input_total": len(payload.events),
                "accepted_rate": (accepted / len(payload.events)) if payload.events else 0,
            }
            completed = self.task_repository.mark_completed(task.id, result=result, metrics=metrics)
            return self._to_task_response(completed or task)
        except Exception as exc:
            failed = self.task_repository.mark_failed(task.id, error_message=str(exc))
            return self._to_task_response(failed or task)

    def run_pull_job(self, payload: S1PullNowRequestModel) -> S1TaskResponseModel:
        date_window = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
        key_source = payload.source_system or "all"
        idempotency_key = f"s1_ingest_pull:{key_source}:{date_window.isoformat()}"
        existing = self.task_repository.get_by_idempotency_key(idempotency_key)
        if existing is not None and existing.status in {"running", "completed"}:
            return self._to_task_response(existing)

        task = existing or self.task_repository.create_pending(
            task_type="s1_ingest_pull",
            idempotency_key=idempotency_key,
            trace_id=uuid4(),
            business_id=None,
            date_window=date_window,
        )
        _ = self.task_repository.mark_running(task.id)
        completed = self.task_repository.mark_completed(
            task.id,
            result={"accepted": 0, "duplicate": 0, "filtered": 0, "note": "pull adapter not configured"},
            metrics={"input_total": 0},
        )
        return self._to_task_response(completed or task)

    def _build_push_idempotency_key(self, events: list[S1EventInputModel], date_window: datetime) -> str:
        digest_source = "|".join(sorted(event.event_key for event in events))
        digest = hashlib.sha1(digest_source.encode("utf-8")).hexdigest()
        return f"s1_ingest_push:{date_window.isoformat()}:{digest}"

    def _to_task_response(self, task: TaskExecutionEntity) -> S1TaskResponseModel:
        return S1TaskResponseModel(
            task_id=str(task.id),
            status=task.status,
            result=task.result or {},
        )
