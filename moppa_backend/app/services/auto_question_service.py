import json
import logging
from datetime import datetime, timedelta, timezone
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from uuid import uuid4

from sqlalchemy.orm import Session

from app.config import settings
from app.db.models import EventEntity, QuestionTemplateEntity, TaskExecutionEntity
from app.models.s1_ingest_model import S1TaskResponseModel
from app.repositories.event_repository import EventRepository
from app.repositories.question_template_repository import QuestionTemplateRepository
from app.repositories.task_execution_repository import TaskExecutionRepository

_logger = logging.getLogger(__name__)


class AutoQuestionService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.event_repository = EventRepository(db)
        self.template_repository = QuestionTemplateRepository(db)
        self.task_repository = TaskExecutionRepository(db)

    def run_auto_question_job(self, force_run: bool = False) -> S1TaskResponseModel:
        date_window = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
        if force_run:
            idempotency_key = f"auto_question:manual:{datetime.now(timezone.utc).isoformat()}:{uuid4()}"
            existing = None
        else:
            idempotency_key = f"auto_question:{date_window.isoformat()}"
            existing = self.task_repository.get_by_idempotency_key(idempotency_key)
            if existing is not None and existing.status in {"running", "completed"}:
                return self._to_task_response(existing)

        task = existing
        if task is None:
            task = self.task_repository.create_pending(
                task_type="auto_question",
                idempotency_key=idempotency_key,
                trace_id=uuid4(),
                business_id=None,
                date_window=date_window,
            )
        _ = self.task_repository.mark_running(task.id)

        try:
            self._validate_runtime_config()
            templates = self.template_repository.list_all()
            grouped_templates = self._build_grouped_templates(templates)
            if not grouped_templates:
                result = {
                    "processed_batches": 0,
                    "processed_events": 0,
                    "generated_questions": 0,
                    "message": "No available question templates",
                }
                metrics = {"template_count": 0, "api_call_count": 0}
                completed = self.task_repository.mark_completed(task.id, result=result, metrics=metrics)
                return self._to_task_response(completed or task)

            now = datetime.now(timezone.utc)
            range_start, range_end = self._resolve_event_time_range(now)
            batch_size = settings.auto_question_batch_size
            offset = 0

            processed_batches = 0
            processed_events = 0
            generated_questions = 0
            api_call_count = 0
            batch_logs: list[dict[str, object]] = []

            while True:
                if range_start is None or range_end is None:
                    events = self.event_repository.list_passed(limit=batch_size, offset=offset)
                else:
                    events = self.event_repository.list_passed_today(
                        day_start=range_start,
                        day_end=range_end,
                        limit=batch_size,
                        offset=offset,
                    )
                if not events:
                    break

                payload: dict[str, object] = {
                    "sources": self._build_sources(events),
                    "question_templates": grouped_templates,
                    "skip_filter": False,
                    "skip_dedup": False,
                }
                response_data = self._call_generate_api(payload)
                api_call_count += 1

                questions = response_data.get("questions")
                question_count = len(questions) if isinstance(questions, list) else 0
                generated_questions += question_count
                processed_batches += 1
                processed_events += len(events)

                log_item: dict[str, object] = {
                    "batch": processed_batches,
                    "event_count": len(events),
                    "generated_question_count": question_count,
                    "event_ids": [str(event.id) for event in events],
                }
                batch_logs.append(log_item)
                _logger.info(
                    "Auto question batch completed: task_id=%s batch=%s event_count=%s generated_question_count=%s",
                    str(task.id),
                    processed_batches,
                    len(events),
                    question_count,
                )
                if isinstance(questions, list) and questions:
                    _logger.info(
                        "Auto question generated questions: task_id=%s batch=%s questions=%s",
                        str(task.id),
                        processed_batches,
                        json.dumps(questions, ensure_ascii=False),
                    )

                offset += len(events)

            template_count = 0
            for group in grouped_templates:
                templates_value = group.get("templates")
                if isinstance(templates_value, list):
                    template_count += len(templates_value)

            result = {
                "event_scope": settings.auto_question_event_scope,
                "processed_batches": processed_batches,
                "processed_events": processed_events,
                "generated_questions": generated_questions,
                "batch_logs": batch_logs,
            }
            metrics = {
                "template_group_count": len(grouped_templates),
                "template_count": template_count,
                "api_call_count": api_call_count,
            }
            completed = self.task_repository.mark_completed(task.id, result=result, metrics=metrics)
            return self._to_task_response(completed or task)
        except Exception as exc:
            _logger.exception("Auto question task failed: task_id=%s", str(task.id))
            failed = self.task_repository.mark_failed(task.id, error_message=str(exc), max_attempts=3)
            return self._to_task_response(failed or task)

    def _validate_runtime_config(self) -> None:
        if not settings.auto_question_generate_url.strip():
            raise ValueError("AUTO_QUESTION_GENERATE_URL is required")

    def _resolve_event_time_range(self, now: datetime) -> tuple[datetime | None, datetime | None]:
        scope = settings.auto_question_event_scope
        if scope == "all":
            return None, None
        if scope == "today":
            start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            return start, start + timedelta(days=1)
        if scope == "week":
            day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            start = day_start - timedelta(days=day_start.weekday())
            return start, start + timedelta(days=7)
        if scope == "month":
            start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            if start.month == 12:
                end = start.replace(year=start.year + 1, month=1)
            else:
                end = start.replace(month=start.month + 1)
            return start, end
        start = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        end = start.replace(year=start.year + 1)
        return start, end

    def _build_sources(self, events: list[EventEntity]) -> list[dict[str, object]]:
        sources: list[dict[str, object]] = []
        for item in events:
            url = (item.url or "").strip() or "无"
            sources.append(
                {
                    "id": str(item.id),
                    "title": item.title,
                    "content": item.content,
                    "input_type": "news",
                    "url": url,
                }
            )
        return sources

    def _build_grouped_templates(self, templates: list[QuestionTemplateEntity]) -> list[dict[str, object]]:
        domain_groups: dict[str, list[dict[str, object]]] = {}
        for template in templates:
            domain = template.event_domain.strip()
            if not domain:
                continue
            group = domain_groups.setdefault(domain, [])
            group.append(
                {
                    "id": str(template.id),
                    "template": template.question_template,
                    "level": template.difficulty_level,
                    "options_type": template.candidate_answer_type,
                    "event_type": template.event_type,
                }
            )
        return [
            {
                "domain": domain,
                "templates": domain_groups[domain],
            }
            for domain in sorted(domain_groups.keys())
            if domain_groups[domain]
        ]

    def _call_generate_api(self, payload: dict[str, object]) -> dict[str, object]:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        request = Request(
            url=settings.auto_question_generate_url,
            data=body,
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            method="POST",
        )
        try:
            with urlopen(request, timeout=settings.auto_question_timeout_seconds) as response:
                raw = response.read().decode("utf-8")
                parsed = json.loads(raw) if raw.strip() else {}
                if isinstance(parsed, dict):
                    return parsed
                return {"raw": parsed}
        except HTTPError as exc:
            error_body = exc.read().decode("utf-8", errors="ignore") if exc.fp is not None else ""
            raise RuntimeError(
                f"Auto question API HTTP error: status={exc.code} body={error_body[:500]}"
            ) from exc
        except URLError as exc:
            raise RuntimeError(f"Auto question API connection error: {exc.reason}") from exc
        except TimeoutError as exc:
            raise RuntimeError("Auto question API request timed out") from exc

    def _to_task_response(self, task: TaskExecutionEntity) -> S1TaskResponseModel:
        return S1TaskResponseModel(
            task_id=str(task.id),
            status=task.status,
            result=task.result or {},
        )
