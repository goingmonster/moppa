import logging
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy.orm import Session

from app.db.models import TaskExecutionEntity
from app.models.s1_ingest_model import S1TaskResponseModel
from app.repositories.question_repository import QuestionRepository
from app.repositories.task_execution_repository import TaskExecutionRepository


_logger = logging.getLogger(__name__)


class QuestionExpiryService:
    def __init__(self, db: Session) -> None:
        self.db: Session = db
        self.question_repository: QuestionRepository = QuestionRepository(db)
        self.task_repository: TaskExecutionRepository = TaskExecutionRepository(db)

    def run_expiry_check_job(self, force_run: bool = False) -> S1TaskResponseModel:
        date_window = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
        if force_run:
            idempotency_key = f"question_expiry:manual:{datetime.now(timezone.utc).isoformat()}:{uuid4()}"
            existing = None
        else:
            idempotency_key = f"question_expiry:{date_window.isoformat()}"
            existing = self.task_repository.get_by_idempotency_key(idempotency_key)
            if existing is not None and existing.status in {"running", "completed"}:
                return self._to_task_response(existing)

        task = existing
        if task is None:
            task = self.task_repository.create_pending(
                task_type="question_expiry",
                idempotency_key=idempotency_key,
                trace_id=uuid4(),
                business_id=None,
                date_window=date_window,
            )
        _ = self.task_repository.mark_running(task.id)

        try:
            now = datetime.now(timezone.utc)
            expired_questions = self.question_repository.list_expired(now)
            _logger.info(
                "Question expiry check started: task_id=%s expired_count=%s",
                str(task.id),
                len(expired_questions),
            )

            expired_count = 0
            skipped_count = 0

            for question in expired_questions:
                if question.status == "expired":
                    skipped_count += 1
                    continue
                question.status = "expired"
                expired_count += 1

            self.db.commit()

            result: dict[str, object] = {
                "scanned": len(expired_questions),
                "expired_count": expired_count,
                "skipped": skipped_count,
            }
            metrics: dict[str, object] = {
                "expiry_rate": (expired_count / len(expired_questions)) if expired_questions else 0,
            }
            _logger.info(
                "Question expiry check completed: task_id=%s scanned=%s expired=%s skipped=%s",
                str(task.id),
                len(expired_questions),
                expired_count,
                skipped_count,
            )
            completed = self.task_repository.mark_completed(task.id, result=result, metrics=metrics)
            return self._to_task_response(completed or task)
        except Exception as exc:
            _logger.exception("Question expiry check task failed: task_id=%s", str(task.id))
            failed = self.task_repository.mark_failed(task.id, error_message=str(exc), max_attempts=3)
            return self._to_task_response(failed or task)

    def _to_task_response(self, task: TaskExecutionEntity) -> S1TaskResponseModel:
        return S1TaskResponseModel(
            task_id=str(task.id),
            status=task.status,
            result=task.result or {},
        )
