from __future__ import annotations

import logging
from datetime import datetime, timezone
from time import perf_counter
from typing import cast
from uuid import uuid4

from sqlalchemy.orm import Session

from app.config import settings
from app.db.models import TaskExecutionEntity
from app.integrations.tavily_search_client import TavilySearchClient
from app.models.s1_ingest_model import S1TaskResponseModel
from app.repositories.data_source_repository import DataSourceRepository
from app.repositories.event_repository import EventRepository
from app.repositories.task_execution_repository import TaskExecutionRepository
from app.services.tavily_event_extraction_service import TavilyEventExtractionService


_logger = logging.getLogger(__name__)


class TavilyIngestService:
    def __init__(self, db: Session) -> None:
        self.db: Session = db
        self.task_repository: TaskExecutionRepository = TaskExecutionRepository(db)
        self.data_source_repository: DataSourceRepository = DataSourceRepository(db)
        self.event_repository: EventRepository = EventRepository(db)
        self.search_client: TavilySearchClient = TavilySearchClient(settings.tavily_keys)
        self.extraction_service: TavilyEventExtractionService = TavilyEventExtractionService()

    def run_ingest_job(self, force_run: bool = False) -> S1TaskResponseModel:
        self._validate_runtime_config()
        task_started_at = perf_counter()
        date_window = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
        if force_run:
            idempotency_key = f"tavily_ingest:manual:{datetime.now(timezone.utc).isoformat()}:{uuid4()}"
            existing = None
        else:
            idempotency_key = f"tavily_ingest:{date_window.isoformat()}"
            existing = self.task_repository.get_by_idempotency_key(idempotency_key)
            if existing is not None and existing.status in {"running", "completed"}:
                return self._to_task_response(existing)

        task = existing
        if task is None:
            task = self.task_repository.create_pending(
                task_type="tavily_ingest",
                idempotency_key=idempotency_key,
                trace_id=uuid4(),
                business_id=None,
                date_window=date_window,
            )
        _ = self.task_repository.mark_running(task.id)

        try:
            _logger.info(
                "Tavily ingest task started: task_id=%s force_run=%s topics=%s max_results=%s search_depth=%s time_range=%s",
                str(task.id),
                force_run,
                list(settings.tavily_topics),
                settings.tavily_max_results,
                settings.tavily_search_depth,
                settings.tavily_news_time_range,
            )
            self.data_source_repository.ensure_source_system("tavily")
            result: dict[str, object] = {
                "topics": list(settings.tavily_topics),
                "topic_runs": [],
                "fetched": 0,
                "generated": 0,
                "accepted": 0,
                "duplicate": 0,
                "failed_topics": 0,
            }
            metrics: dict[str, object] = {
                "topic_count": len(settings.tavily_topics),
                "tavily_call_count": 0,
                "event_acceptance_rate": 0,
                "fetch_duration_seconds": 0.0,
                "extract_duration_seconds": 0.0,
                "store_duration_seconds": 0.0,
                "total_duration_seconds": 0.0,
                "topic_duration_seconds": {},
            }

            for topic in settings.tavily_topics:
                topic_started_at = perf_counter()
                _logger.info(
                    "Tavily ingest topic started: task_id=%s topic=%s",
                    str(task.id),
                    topic,
                )
                topic_result: dict[str, object] = {
                    "topic": topic,
                    "status": "completed",
                    "fetched": 0,
                    "generated": 0,
                    "accepted": 0,
                    "duplicate": 0,
                    "fetch_duration_seconds": 0.0,
                    "extract_duration_seconds": 0.0,
                    "store_duration_seconds": 0.0,
                    "total_duration_seconds": 0.0,
                }
                try:
                    fetch_started_at = perf_counter()
                    search_results = self.search_client.search_news(
                        query=topic,
                        max_results=settings.tavily_max_results,
                        search_depth=settings.tavily_search_depth,
                        time_range=settings.tavily_news_time_range,
                    )
                    fetch_duration_seconds = self._round_seconds(perf_counter() - fetch_started_at)
                    topic_result["fetch_duration_seconds"] = fetch_duration_seconds
                    metrics["fetch_duration_seconds"] = self._float_value(metrics, "fetch_duration_seconds") + fetch_duration_seconds
                    metrics["tavily_call_count"] = self._int_value(metrics, "tavily_call_count") + 1
                    topic_result["fetched"] = len(search_results)
                    result["fetched"] = self._int_value(result, "fetched") + len(search_results)
                    _logger.info(
                        "Tavily ingest topic fetched: task_id=%s topic=%s fetched=%s fetch_duration_seconds=%s sample_urls=%s",
                        str(task.id),
                        topic,
                        len(search_results),
                        fetch_duration_seconds,
                        [item.url for item in search_results[:3] if item.url],
                    )

                    extract_started_at = perf_counter()
                    events = self.extraction_service.build_events(topic=topic, results=search_results)
                    extract_duration_seconds = self._round_seconds(perf_counter() - extract_started_at)
                    topic_result["extract_duration_seconds"] = extract_duration_seconds
                    metrics["extract_duration_seconds"] = self._float_value(metrics, "extract_duration_seconds") + extract_duration_seconds
                    topic_result["generated"] = len(events)
                    result["generated"] = self._int_value(result, "generated") + len(events)
                    _logger.info(
                        "Tavily ingest topic transformed: task_id=%s topic=%s generated=%s extract_duration_seconds=%s sample_titles=%s",
                        str(task.id),
                        topic,
                        len(events),
                        extract_duration_seconds,
                        [item.title for item in events[:3]],
                    )

                    store_started_at = perf_counter()
                    for event in events:
                        entity, created = self.event_repository.ingest_event(
                            event_key=event.event_key,
                            title=event.title,
                            content=event.content,
                            source_system=event.source_system,
                            credibility_level=event.credibility_level,
                            event_time=event.event_time,
                            url=event.url,
                            trace_id=event.trace_id,
                            metadata={
                                "topic": topic,
                                "origin": "tavily",
                            },
                        )
                        if created:
                            topic_result["accepted"] = self._int_value(topic_result, "accepted") + 1
                            result["accepted"] = self._int_value(result, "accepted") + 1
                            _ = self.event_repository.set_filter_result(
                                entity.id,
                                status="pending",
                                reasons=["WAITING_REVIEW_TAVILY_IMPORT"],
                            )
                        else:
                            topic_result["duplicate"] = self._int_value(topic_result, "duplicate") + 1
                            result["duplicate"] = self._int_value(result, "duplicate") + 1
                    store_duration_seconds = self._round_seconds(perf_counter() - store_started_at)
                    topic_result["store_duration_seconds"] = store_duration_seconds
                    metrics["store_duration_seconds"] = self._float_value(metrics, "store_duration_seconds") + store_duration_seconds
                    _logger.info(
                        "Tavily ingest topic stored: task_id=%s topic=%s accepted=%s duplicate=%s total_generated=%s store_duration_seconds=%s",
                        str(task.id),
                        topic,
                        self._int_value(topic_result, "accepted"),
                        self._int_value(topic_result, "duplicate"),
                        self._int_value(topic_result, "generated"),
                        store_duration_seconds,
                    )
                except Exception as exc:
                    _logger.exception("Tavily topic ingest failed: task_id=%s topic=%s", str(task.id), topic)
                    topic_result["status"] = "failed"
                    topic_result["error"] = str(exc)
                    result["failed_topics"] = self._int_value(result, "failed_topics") + 1

                topic_duration_seconds = self._round_seconds(perf_counter() - topic_started_at)
                topic_result["total_duration_seconds"] = topic_duration_seconds
                topic_runs = result.get("topic_runs")
                if isinstance(topic_runs, list):
                    cast_runs = cast(list[dict[str, object]], topic_runs)
                    cast_runs.append(topic_result)
                topic_duration_metrics = self._topic_duration_metrics(metrics)
                topic_duration_metrics[topic] = topic_duration_seconds
                metrics["event_acceptance_rate"] = (
                    self._int_value(result, "accepted") / self._int_value(result, "generated")
                    if self._int_value(result, "generated")
                    else 0
                )
                metrics["total_duration_seconds"] = self._round_seconds(perf_counter() - task_started_at)
                _logger.info(
                    "Tavily ingest topic finished: task_id=%s topic=%s status=%s fetched=%s generated=%s accepted=%s duplicate=%s failed_topics=%s topic_duration_seconds=%s",
                    str(task.id),
                    topic,
                    str(topic_result.get("status") or "completed"),
                    self._int_value(topic_result, "fetched"),
                    self._int_value(topic_result, "generated"),
                    self._int_value(topic_result, "accepted"),
                    self._int_value(topic_result, "duplicate"),
                    self._int_value(result, "failed_topics"),
                    topic_duration_seconds,
                )
                _ = self.task_repository.update_progress(task.id, result=result, metrics=metrics)

            if self._int_value(result, "failed_topics") >= len(settings.tavily_topics):
                raise RuntimeError("All Tavily topic ingests failed")

            metrics["total_duration_seconds"] = self._round_seconds(perf_counter() - task_started_at)
            _logger.info(
                "Tavily ingest task completed: task_id=%s fetched=%s generated=%s accepted=%s duplicate=%s failed_topics=%s acceptance_rate=%s fetch_duration_seconds=%s extract_duration_seconds=%s store_duration_seconds=%s total_duration_seconds=%s",
                str(task.id),
                self._int_value(result, "fetched"),
                self._int_value(result, "generated"),
                self._int_value(result, "accepted"),
                self._int_value(result, "duplicate"),
                self._int_value(result, "failed_topics"),
                metrics.get("event_acceptance_rate"),
                metrics.get("fetch_duration_seconds"),
                metrics.get("extract_duration_seconds"),
                metrics.get("store_duration_seconds"),
                metrics.get("total_duration_seconds"),
            )
            completed = self.task_repository.mark_completed(task.id, result=result, metrics=metrics)
            return self._to_task_response(completed or task)
        except Exception as exc:
            _logger.exception("Tavily ingest task failed: task_id=%s", str(task.id))
            failed = self.task_repository.mark_failed(task.id, error_message=str(exc), max_attempts=3)
            return self._to_task_response(failed or task)

    def _validate_runtime_config(self) -> None:
        if not settings.tavily_keys:
            raise ValueError("TAVILY_KEYS is required")
        if not settings.tavily_topics:
            raise ValueError("TAVILY_TOPICS is required")
        if not settings.tavily_openai_model:
            raise ValueError("TAVILY_OPENAI_MODEL is required")
        if not settings.tavily_openai_base_url:
            raise ValueError("TAVILY_OPENAI_BASE_URL is required")
        if not settings.tavily_openai_api_key:
            raise ValueError("TAVILY_OPENAI_API_KEY is required")

    def _to_task_response(self, task: TaskExecutionEntity) -> S1TaskResponseModel:
        return S1TaskResponseModel(
            task_id=str(task.id),
            status=task.status,
            result=task.result or {},
        )

    def _int_value(self, payload: dict[str, object], key: str) -> int:
        value = payload.get(key)
        return value if isinstance(value, int) else 0

    def _float_value(self, payload: dict[str, object], key: str) -> float:
        value = payload.get(key)
        return float(value) if isinstance(value, (int, float)) else 0.0

    def _round_seconds(self, value: float) -> float:
        return round(value, 3)

    def _topic_duration_metrics(self, metrics: dict[str, object]) -> dict[str, float]:
        value = metrics.get("topic_duration_seconds")
        if isinstance(value, dict):
            typed = cast(dict[str, float], value)
            return typed
        typed: dict[str, float] = {}
        metrics["topic_duration_seconds"] = typed
        return typed
