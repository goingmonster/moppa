from collections.abc import Callable
from http.client import RemoteDisconnected
import json
import logging
import math
import time
from datetime import datetime, timedelta, timezone
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from app.config import settings
from app.db.models import EventEntity, QuestionTemplateEntity, TaskExecutionEntity
from app.db.session import SessionLocal
from app.models.question_model import QuestionCreateModel
from app.models.s1_ingest_model import S1TaskResponseModel
from app.repositories.event_repository import EventRepository
from app.repositories.question_repository import QuestionRepository
from app.repositories.question_template_repository import QuestionTemplateRepository
from app.repositories.task_execution_repository import TaskExecutionRepository

_logger = logging.getLogger(__name__)


class AutoQuestionService:
    _session_factory: Callable[[], Session] = SessionLocal

    def __init__(self, db: Session) -> None:
        self.db = db
        self.event_repository = EventRepository(db)
        self.question_repository = QuestionRepository(db)
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
            total_events = self.event_repository.count_passed(
                day_start=range_start,
                day_end=range_end,
                source_systems=settings.auto_question_source_systems,
            )
            total_batches = math.ceil(total_events / batch_size) if total_events > 0 else 0

            _logger.info(
                "Auto question task started: task_id=%s total_events=%s batch_size=%s total_batches=%s scope=%s",
                str(task.id),
                total_events,
                batch_size,
                total_batches,
                settings.auto_question_event_scope,
            )

            processed_batches = 0
            processed_events = 0
            generated_questions = 0
            saved_questions = 0
            failed_batches = 0
            failed_events = 0
            api_call_count = 0
            batch_logs: list[dict[str, object]] = []

            while True:
                if range_start is None or range_end is None:
                    events = self.event_repository.list_passed(
                        limit=batch_size,
                        offset=offset,
                        source_systems=settings.auto_question_source_systems,
                    )
                else:
                    events = self.event_repository.list_passed_today(
                        day_start=range_start,
                        day_end=range_end,
                        limit=batch_size,
                        offset=offset,
                        source_systems=settings.auto_question_source_systems,
                    )
                if not events:
                    break

                payload: dict[str, object] = {
                    "sources": self._build_sources(events),
                    "question_templates": grouped_templates,
                    "skip_filter": False,
                    "skip_dedup": False,
                }
                _logger.info(
                    "Auto question API call start: task_id=%s batch=%s/%s event_count=%s url=%s",
                    str(task.id),
                    processed_batches + 1,
                    total_batches,
                    len(events),
                    settings.auto_question_generate_url,
                )
                try:
                    response_data = self._call_generate_api_with_retry(
                        payload=payload,
                        task_id=str(task.id),
                        batch_number=processed_batches + 1,
                        total_batches=total_batches,
                    )
                    api_call_count += 1
                    _logger.info(
                        "Auto question API response payload: task_id=%s batch=%s/%s response=%s",
                        str(task.id),
                        processed_batches + 1,
                        total_batches,
                        json.dumps(response_data, ensure_ascii=False),
                    )
                except RuntimeError as exc:
                    failed_batches += 1
                    failed_events += len(events)
                    processed_batches += 1
                    offset += len(events)

                    log_item: dict[str, object] = {
                        "batch": processed_batches,
                        "event_count": len(events),
                        "status": "failed",
                        "error": str(exc),
                        "event_ids": [str(event.id) for event in events],
                    }
                    batch_logs.append(log_item)
                    _logger.error(
                        "Auto question batch failed and skipped: task_id=%s batch=%s/%s batch_event_count=%s error=%s",
                        str(task.id),
                        processed_batches,
                        total_batches,
                        len(events),
                        str(exc),
                    )

                    progress_result = {
                        "event_scope": settings.auto_question_event_scope,
                        "total_events": total_events,
                        "total_batches": total_batches,
                        "processed_batches": processed_batches,
                        "processed_events": processed_events,
                        "generated_questions": generated_questions,
                        "saved_questions": saved_questions,
                        "failed_batches": failed_batches,
                        "failed_events": failed_events,
                        "batch_logs": batch_logs,
                    }
                    progress_template_count = 0
                    for group in grouped_templates:
                        group_templates = group.get("templates")
                        if isinstance(group_templates, list):
                            progress_template_count += len(group_templates)
                    progress_metrics = {
                        "template_group_count": len(grouped_templates),
                        "template_count": progress_template_count,
                        "api_call_count": api_call_count,
                    }
                    _ = self.task_repository.update_progress(task.id, progress_result, progress_metrics)
                    continue

                questions = response_data.get("questions")
                question_count = len(questions) if isinstance(questions, list) else 0
                saved_count = self._save_generated_questions(questions, events)
                generated_questions += question_count
                saved_questions += saved_count
                processed_batches += 1
                processed_events += len(events)
                remaining_events = max(total_events - processed_events, 0)
                _ = self.event_repository.batch_mark_matched([event.id for event in events])

                log_item: dict[str, object] = {
                    "batch": processed_batches,
                    "event_count": len(events),
                    "generated_question_count": question_count,
                    "saved_question_count": saved_count,
                    "event_ids": [str(event.id) for event in events],
                }
                batch_logs.append(log_item)
                progress_result = {
                    "event_scope": settings.auto_question_event_scope,
                    "total_events": total_events,
                    "total_batches": total_batches,
                    "processed_batches": processed_batches,
                    "processed_events": processed_events,
                    "generated_questions": generated_questions,
                    "saved_questions": saved_questions,
                    "failed_batches": failed_batches,
                    "failed_events": failed_events,
                    "batch_logs": batch_logs,
                }
                progress_template_count = 0
                for group in grouped_templates:
                    group_templates = group.get("templates")
                    if isinstance(group_templates, list):
                        progress_template_count += len(group_templates)
                progress_metrics = {
                    "template_group_count": len(grouped_templates),
                    "template_count": progress_template_count,
                    "api_call_count": api_call_count,
                }
                _ = self.task_repository.update_progress(task.id, progress_result, progress_metrics)
                _logger.info(
                    "Auto question batch completed: task_id=%s batch=%s/%s batch_event_count=%s processed_events=%s remaining_events=%s generated_question_count=%s saved_question_count=%s",
                    str(task.id),
                    processed_batches,
                    total_batches,
                    len(events),
                    processed_events,
                    remaining_events,
                    question_count,
                    saved_count,
                )
                if isinstance(questions, list) and questions:
                    _logger.info(
                        "Auto question generated questions: task_id=%s batch=%s questions=%s",
                        str(task.id),
                        processed_batches,
                        json.dumps(questions, ensure_ascii=False),
                    )
                    _logger.info(
                        "Auto question generated question summaries: task_id=%s batch=%s questions=%s",
                        str(task.id),
                        processed_batches,
                        json.dumps(self._build_generated_question_log_entries(questions), ensure_ascii=False),
                    )

                offset += len(events)

            template_count = 0
            for group in grouped_templates:
                templates_value = group.get("templates")
                if isinstance(templates_value, list):
                    template_count += len(templates_value)

            result = {
                "event_scope": settings.auto_question_event_scope,
                "total_events": total_events,
                "total_batches": total_batches,
                "processed_batches": processed_batches,
                "processed_events": processed_events,
                "generated_questions": generated_questions,
                "saved_questions": saved_questions,
                "failed_batches": failed_batches,
                "failed_events": failed_events,
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
            try:
                self.db.rollback()
            except Exception:
                _logger.exception("Auto question rollback failed: task_id=%s", str(task.id))
            try:
                failed = self.task_repository.mark_failed(task.id, error_message=str(exc), max_attempts=3)
                return self._to_task_response(failed or task)
            except Exception:
                _logger.exception("Auto question mark_failed failed: task_id=%s", str(task.id))
                failed = self._mark_failed_with_fresh_session(task.id, str(exc))
                if failed is not None:
                    return self._to_task_response(failed)
                return self._to_task_response(task)
            finally:
                try:
                    self.db.close()
                except Exception:
                    _logger.exception("Auto question session close failed: task_id=%s", str(task.id))

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

    def _save_generated_questions(self, questions_obj: object, batch_events: list[EventEntity]) -> int:
        if not isinstance(questions_obj, list):
            return 0

        event_by_url_title: dict[tuple[str, str], UUID] = {}
        event_by_url: dict[str, UUID] = {}
        event_by_source_id: dict[str, UUID] = {}
        event_by_event_key: dict[str, UUID] = {}
        for event in batch_events:
            url = (event.url or "").strip()
            title = (event.title or "").strip()
            event_by_source_id[str(event.id)] = event.id
            if event.event_key:
                event_by_event_key[event.event_key.strip()] = event.id
            if url:
                event_by_url[url] = event.id
            if url and title:
                event_by_url_title[(url, title)] = event.id

        saved = 0
        for item in questions_obj:
            if not isinstance(item, dict):
                continue
            content_value = item.get("question")
            if not isinstance(content_value, str) or not content_value.strip():
                continue

            template_id = self._parse_template_uuid(item.get("template_id"))
            level = self._parse_level(item.get("level"))
            deadline = self._parse_deadline(item.get("deadline"))
            if deadline is None:
                continue

            candidate_answers_value = item.get("candidate_answers")
            answer_space = self._build_answer_space(candidate_answers_value)
            match_score = self._parse_match_score(item.get("match_score"))
            event_domain = item.get("event_domain") if isinstance(item.get("event_domain"), str) else None
            event_type = item.get("event_type") if isinstance(item.get("event_type"), str) else None
            area = item.get("area") if isinstance(item.get("area"), str) else None
            input_type = item.get("input_type") if isinstance(item.get("input_type"), str) else None
            background = item.get("background") if isinstance(item.get("background"), str) else None

            resolution_criteria_value = item.get("resolution_criteria")
            verification_conditions: str | None = None
            if isinstance(resolution_criteria_value, str) and resolution_criteria_value.strip():
                verification_conditions = resolution_criteria_value.strip()

            linked_event_ids = self._resolve_question_event_ids(
                source_id_obj=item.get("id"),
                source_url_obj=item.get("source_url"),
                event_by_source_id=event_by_source_id,
                event_by_event_key=event_by_event_key,
                event_by_url_title=event_by_url_title,
                event_by_url=event_by_url,
                batch_events=batch_events,
            )
            payload = QuestionCreateModel(
                event_id=linked_event_ids[0] if linked_event_ids else None,
                event_ids=linked_event_ids,
                template_id=template_id,
                level=level,
                content=content_value.strip(),
                match_score=match_score,
                event_domain=event_domain.strip() if event_domain else None,
                event_type=event_type.strip() if event_type else None,
                area=area.strip() if area else None,
                input_type=input_type.strip() if input_type else None,
                background=background.strip() if background else None,
                answer_space=answer_space,
                verification_conditions=verification_conditions,
                deadline=deadline,
                status="matched",
                trace_id=uuid4(),
            )
            try:
                _ = self.question_repository.create(payload)
                saved += 1
            except Exception:
                _logger.exception("Auto question save failed for one generated question")
                try:
                    self.db.rollback()
                except Exception:
                    _logger.exception("Auto question rollback failed while saving generated question")

        return saved

    def _resolve_question_event_ids(
        self,
        source_id_obj: object,
        source_url_obj: object,
        event_by_source_id: dict[str, UUID],
        event_by_event_key: dict[str, UUID],
        event_by_url_title: dict[tuple[str, str], UUID],
        event_by_url: dict[str, UUID],
        batch_events: list[EventEntity],
    ) -> list[UUID]:
        resolved: list[UUID] = []

        source_id = str(source_id_obj).strip() if source_id_obj is not None else ""
        if source_id:
            mapped_by_id = event_by_source_id.get(source_id)
            if mapped_by_id is not None:
                return [mapped_by_id]
            mapped_by_key = event_by_event_key.get(source_id)
            if mapped_by_key is not None:
                return [mapped_by_key]

        if isinstance(source_url_obj, list):
            for row in source_url_obj:
                if not isinstance(row, dict):
                    continue
                url_value = row.get("url")
                title_value = row.get("title")
                url = url_value.strip() if isinstance(url_value, str) else ""
                title = title_value.strip() if isinstance(title_value, str) else ""
                match_id: UUID | None = None
                if url and title:
                    match_id = event_by_url_title.get((url, title))
                if match_id is None and url:
                    match_id = event_by_url.get(url)
                if match_id is not None and match_id not in resolved:
                    resolved.append(match_id)
        if resolved:
            return resolved
        if batch_events:
            return [batch_events[0].id]
        return []

    def _parse_template_uuid(self, value: object) -> UUID | None:
        if not isinstance(value, str):
            return None
        text = value.strip()
        if not text:
            return None
        try:
            return UUID(text)
        except ValueError:
            return None

    def _parse_level(self, value: object) -> int:
        if isinstance(value, str):
            text = value.strip().upper()
            if text.startswith("L") and len(text) > 1 and text[1:].isdigit():
                parsed = int(text[1:])
                if 1 <= parsed <= 4:
                    return parsed
        if isinstance(value, int) and 1 <= value <= 4:
            return value
        return 1

    def _parse_deadline(self, value: object) -> datetime | None:
        if not isinstance(value, str):
            return None
        text = value.strip()
        if not text:
            return None
        try:
            parsed = datetime.fromisoformat(text)
        except ValueError:
            try:
                parsed = datetime.fromisoformat(f"{text}T00:00:00")
            except ValueError:
                return None
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)

    def _build_answer_space(self, value: object) -> str | None:
        if isinstance(value, str) and value.strip():
            return value.strip()
        if value is None:
            return None
        try:
            serialized = json.dumps(value, ensure_ascii=False)
        except (TypeError, ValueError):
            serialized = str(value)
        serialized = serialized.strip()
        if not serialized:
            return None
        return serialized

    def _build_generated_question_log_entries(self, questions_obj: object) -> list[dict[str, object]]:
        if not isinstance(questions_obj, list):
            return []

        log_entries: list[dict[str, object]] = []
        for index, item in enumerate(questions_obj, start=1):
            question_text: str | None = None
            answer_space: str | None = None
            if isinstance(item, dict):
                raw_question = item.get("question")
                if isinstance(raw_question, str) and raw_question.strip():
                    question_text = raw_question.strip()
                answer_space = self._build_answer_space(item.get("candidate_answers"))
            log_entries.append(
                {
                    "index": index,
                    "question": question_text,
                    "answer_space": answer_space,
                }
            )
        return log_entries

    def _parse_match_score(self, value: object) -> float | None:
        if isinstance(value, (int, float)):
            parsed = float(value)
            if parsed >= 0:
                return parsed
            return None
        if isinstance(value, str):
            text = value.strip()
            if not text:
                return None
            try:
                parsed = float(text)
            except ValueError:
                return None
            if parsed >= 0:
                return parsed
        return None

    def _call_generate_api_with_retry(
        self,
        payload: dict[str, object],
        task_id: str,
        batch_number: int,
        total_batches: int,
    ) -> dict[str, object]:
        attempts = settings.auto_question_retry_count + 1
        last_error: RuntimeError | None = None
        for attempt in range(1, attempts + 1):
            try:
                return self._call_generate_api(payload)
            except RuntimeError as exc:
                last_error = exc
                if attempt >= attempts:
                    break
                sleep_seconds = settings.auto_question_retry_backoff_seconds * attempt
                _logger.warning(
                    "Auto question API retry: task_id=%s batch=%s/%s attempt=%s/%s sleep_seconds=%s error=%s",
                    task_id,
                    batch_number,
                    total_batches,
                    attempt + 1,
                    attempts,
                    sleep_seconds,
                    str(exc),
                )
                time.sleep(sleep_seconds)
        if last_error is not None:
            raise last_error
        raise RuntimeError("Auto question API retry failed without error")

    def _call_generate_api(self, payload: dict[str, object]) -> dict[str, object]:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        request = Request(
            url=settings.auto_question_generate_url,
            data=body,
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            method="POST",
        )
        started = time.perf_counter()
        try:
            with urlopen(request, timeout=settings.auto_question_timeout_seconds) as response:
                raw = response.read().decode("utf-8")
                elapsed_ms = int((time.perf_counter() - started) * 1000)
                status_code = response.getcode()
                _logger.info(
                    "Auto question API call success: status=%s elapsed_ms=%s response_size=%s",
                    status_code,
                    elapsed_ms,
                    len(raw),
                )
                parsed = json.loads(raw) if raw.strip() else {}
                if isinstance(parsed, dict):
                    return parsed
                return {"raw": parsed}
        except HTTPError as exc:
            error_body = exc.read().decode("utf-8", errors="ignore") if exc.fp is not None else ""
            elapsed_ms = int((time.perf_counter() - started) * 1000)
            _logger.error(
                "Auto question API call failed: status=%s elapsed_ms=%s body=%s",
                exc.code,
                elapsed_ms,
                error_body[:500],
            )
            raise RuntimeError(
                f"Auto question API HTTP error: status={exc.code} body={error_body[:500]}"
            ) from exc
        except RemoteDisconnected as exc:
            elapsed_ms = int((time.perf_counter() - started) * 1000)
            _logger.error("Auto question API call remote disconnected: elapsed_ms=%s", elapsed_ms)
            raise RuntimeError("Auto question API remote disconnected") from exc
        except URLError as exc:
            elapsed_ms = int((time.perf_counter() - started) * 1000)
            _logger.error(
                "Auto question API call connection error: elapsed_ms=%s reason=%s",
                elapsed_ms,
                exc.reason,
            )
            raise RuntimeError(f"Auto question API connection error: {exc.reason}") from exc
        except TimeoutError as exc:
            elapsed_ms = int((time.perf_counter() - started) * 1000)
            _logger.error(
                "Auto question API call timeout: elapsed_ms=%s timeout_seconds=%s",
                elapsed_ms,
                settings.auto_question_timeout_seconds,
            )
            raise RuntimeError("Auto question API request timed out") from exc

    def _mark_failed_with_fresh_session(
        self, task_id: UUID, error_message: str
    ) -> TaskExecutionEntity | None:
        try:
            with self._session_factory() as db:
                return TaskExecutionRepository(db).mark_failed(
                    task_id,
                    error_message=error_message,
                    max_attempts=3,
                )
        except Exception:
            _logger.exception("Auto question mark_failed fallback failed: task_id=%s", str(task_id))
            return None

    def _to_task_response(self, task: TaskExecutionEntity) -> S1TaskResponseModel:
        return S1TaskResponseModel(
            task_id=str(task.id),
            status=task.status,
            result=task.result or {},
        )
