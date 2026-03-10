import hashlib
from datetime import datetime, timezone
from typing import cast
from uuid import uuid4

from sqlalchemy.orm import Session

from app.db.models import TaskExecutionEntity
from app.config import settings
from app.models.s1_ingest_model import (
    S1DryRunResponseModel,
    S1EventInputModel,
    S1JobDetailResponseModel,
    S1PullNowRequestModel,
    S1PushRequestModel,
    S1TaskResponseModel,
)
from app.repositories.data_source_repository import DataSourceRepository
from app.repositories.event_repository import EventRepository
from app.repositories.source_news_repository import SourceNewsRepository, SourceNewsRow
from app.repositories.system_config_repository import SystemConfigRepository
from app.repositories.task_config_repository import TaskConfigRepository
from app.repositories.task_execution_repository import TaskExecutionRepository
from app.services.event_filter_rule_service import EventFilterRuleService
from app.services.s1_filter_service import S1FilterService


class S1IngestService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.event_repository = EventRepository(db)
        self.data_source_repository = DataSourceRepository(db)
        self.task_repository = TaskExecutionRepository(db)
        self.source_news_repository = SourceNewsRepository()
        self.system_config_repository = SystemConfigRepository(db)
        self.task_config_repository = TaskConfigRepository(db)
        self.rule_service = EventFilterRuleService(db)
        self.filter_service = S1FilterService()

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
        try:
            result, metrics = self._ingest_events(payload.events)
            completed = self.task_repository.mark_completed(task.id, result=result, metrics=metrics)
            return self._to_task_response(completed or task)
        except Exception as exc:
            failed = self.task_repository.mark_failed(
                task.id,
                error_message=str(exc),
                max_attempts=self._resolve_max_attempts("s1_ingest_push"),
            )
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
        try:
            source_system = payload.source_system or "news_event_crawler"
            self.data_source_repository.ensure_source_system(source_system)

            watermark = self._get_pull_watermark()
            rows = cast(
                list[SourceNewsRow],
                self.source_news_repository.fetch_data_test_rows(
                since=watermark,
                limit=self._resolve_source_fetch_limit(),
                ),
            )
            events = [self._map_source_row_to_event(row, source_system=source_system) for row in rows]
            result, metrics = self._ingest_events(events)
            result["fetched"] = len(rows)
            if rows:
                latest = max(row["create_time"] for row in rows)
                self._set_pull_watermark(latest)

            completed = self.task_repository.mark_completed(task.id, result=result, metrics=metrics)
            return self._to_task_response(completed or task)
        except Exception as exc:
            failed = self.task_repository.mark_failed(
                task.id,
                error_message=str(exc),
                max_attempts=self._resolve_max_attempts("s1_ingest_pull"),
            )
            return self._to_task_response(failed or task)

    def get_job_detail(self, task_id: str) -> S1JobDetailResponseModel | None:
        task = self.task_repository.get_by_id(task_id)
        if task is None:
            return None
        return S1JobDetailResponseModel(
            task_id=str(task.id),
            task_type=task.task_type,
            idempotency_key=task.idempotency_key,
            status=task.status,
            attempt_count=task.attempt_count,
            result=task.result or {},
            metrics=task.metrics or {},
            error_message=task.error_message,
            next_retry_at=task.next_retry_at,
            started_at=task.started_at,
            finished_at=task.finished_at,
            created_at=task.created_at,
            trace_id=task.trace_id,
        )

    def dry_run_event(self, event: S1EventInputModel) -> S1DryRunResponseModel:
        active_rules = self.rule_service.list_active_rules()
        status, reasons, applied = self.filter_service.evaluate(event, active_rules)
        return S1DryRunResponseModel(
            status=status,
            reasons=reasons,
            rules_applied_count=applied,
        )

    def _ingest_events(self, events: list[S1EventInputModel]) -> tuple[dict[str, object], dict[str, object]]:
        accepted = 0
        duplicate = 0
        filtered = 0
        skipped = 0
        filtered_reason_stats: dict[str, int] = {}
        active_rules = self.rule_service.list_active_rules()

        for item in events:
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
            status, reasons, _ = self.filter_service.evaluate(item, active_rules)
            _ = self.event_repository.set_filter_result(entity.id, status=status, reasons=reasons)
            if status == "filtered":
                filtered += 1
                for reason in reasons:
                    filtered_reason_stats[reason] = filtered_reason_stats.get(reason, 0) + 1

        result: dict[str, object] = {
            "accepted": accepted,
            "duplicate": duplicate,
            "filtered": filtered,
            "skipped_invalid_source": skipped,
            "rules_applied_count": len(active_rules),
            "filtered_reason_stats": filtered_reason_stats,
        }
        metrics: dict[str, object] = {
            "input_total": len(events),
            "accepted_rate": (accepted / len(events)) if events else 0,
            "filter_pass_rate": ((accepted - filtered) / accepted) if accepted else 0,
        }
        return result, metrics

    def _map_source_row_to_event(self, row: SourceNewsRow, source_system: str) -> S1EventInputModel:
        create_time_raw = row["create_time"]
        if not isinstance(create_time_raw, datetime):
            raise ValueError("create_time is not datetime")
        create_time = create_time_raw
        published = row.get("published")
        event_time: datetime = published if isinstance(published, datetime) else create_time
        url = str(row.get("url") or "")
        title = str(row.get("title_translate") or "")
        content = str(row.get("text_translate") or "")
        source_information = str(row.get("source_information") or "")
        source_site = str(row.get("source_site") or "")
        type_name = str(row.get("type") or "")
        digest_src = f"{url}|{event_time.isoformat()}|{title}|{source_site}"
        event_key = f"crawler:{hashlib.sha1(digest_src.encode('utf-8')).hexdigest()}"
        merged = "\n".join(part for part in [title, content, source_information, source_site, type_name] if part)
        return S1EventInputModel(
            event_key=event_key,
            content=merged or title or content or url,
            source_system=source_system,
            credibility_level=3,
            event_time=event_time,
            trace_id=uuid4(),
        )

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

    def _resolve_max_attempts(self, task_type: str) -> int:
        config = self.task_config_repository.get_by_task_type(task_type)
        if config is None:
            return 3
        raw = config.value.get("max_attempts")
        if isinstance(raw, int) and raw > 0:
            return raw
        if isinstance(raw, str):
            try:
                parsed = int(raw)
                return parsed if parsed > 0 else 3
            except ValueError:
                return 3
        return 3

    def _resolve_source_fetch_limit(self) -> int:
        config = self.task_config_repository.get_by_task_type("s1_ingest_pull")
        if config is None:
            return settings.source_fetch_limit
        raw = config.value.get("source_fetch_limit")
        if isinstance(raw, int) and raw > 0:
            return raw
        if isinstance(raw, str):
            try:
                parsed = int(raw)
                return parsed if parsed > 0 else settings.source_fetch_limit
            except ValueError:
                return settings.source_fetch_limit
        return settings.source_fetch_limit

    def _get_pull_watermark(self) -> datetime | None:
        value = self.system_config_repository.get_value("task.s1_ingest_pull.watermark")
        if value is None:
            return None
        raw = value.get("last_create_time")
        if not isinstance(raw, str):
            return None
        try:
            return datetime.fromisoformat(raw)
        except ValueError:
            return None

    def _set_pull_watermark(self, last_create_time: datetime) -> None:
        _ = self.system_config_repository.upsert_value(
            key="task.s1_ingest_pull.watermark",
            value={"last_create_time": last_create_time.isoformat()},
            description="S1 pull last consumed create_time",
            category="task",
        )
