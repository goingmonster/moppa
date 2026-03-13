import json
import logging
from datetime import datetime, timezone
from uuid import uuid4

from openai import OpenAI
from sqlalchemy.orm import Session

from app.config import settings
from app.db.models import EventEntity, TaskExecutionEntity
from app.models.s1_ingest_model import S1TaskResponseModel
from app.repositories.event_repository import EventRepository
from app.repositories.task_execution_repository import TaskExecutionRepository


_logger = logging.getLogger(__name__)


class S1AutoReviewService:
    TOPICS: tuple[str, ...] = (
        "大国博弈与战略竞争",
        "俄乌战争与欧洲安全",
        "全球政治与选举",
        "亚太军事与安全",
        "中东战争与危机",
    )

    def __init__(self, db: Session) -> None:
        self.db: Session = db
        self.event_repository: EventRepository = EventRepository(db)
        self.task_repository: TaskExecutionRepository = TaskExecutionRepository(db)
        self.client: OpenAI = OpenAI(
            api_key=settings.auto_review_api_key,
            base_url=settings.auto_review_base_url,
            timeout=settings.auto_review_timeout_seconds,
        )

    def run_review_job(self, force_run: bool = False) -> S1TaskResponseModel:
        date_window = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
        if force_run:
            idempotency_key = f"s1_auto_review:manual:{datetime.now(timezone.utc).isoformat()}:{uuid4()}"
            existing = None
        else:
            idempotency_key = f"s1_auto_review:{date_window.isoformat()}"
            existing = self.task_repository.get_by_idempotency_key(idempotency_key)
            if existing is not None and existing.status in {"running", "completed"}:
                return self._to_task_response(existing)

        task = existing
        if task is None:
            task = self.task_repository.create_pending(
                task_type="s1_auto_review",
                idempotency_key=idempotency_key,
                trace_id=uuid4(),
                business_id=None,
                date_window=date_window,
            )
        _ = self.task_repository.mark_running(task.id)

        try:
            self._validate_runtime_config()
            batch_size = max(1, settings.auto_review_batch_size)
            pending_events = self.event_repository.list_pending_for_auto_review(limit=batch_size)
            _logger.info(
                "Auto review started: task_id=%s force_run=%s pending_count=%s batch_size=%s",
                str(task.id),
                force_run,
                len(pending_events),
                batch_size,
            )

            processed = 0
            passed = 0
            filtered = 0
            llm_failed = 0

            for event in pending_events:
                try:
                    topics = self._classify_event_topics(event)
                except Exception:
                    llm_failed += 1
                    _logger.exception(
                        "Auto review classify failed: task_id=%s event_id=%s event_key=%s",
                        str(task.id),
                        str(event.id),
                        event.event_key,
                    )
                    continue

                review_status = "passed" if topics else "filtered"
                reasons = (
                    ["AUTO_REVIEW_TOPIC_MATCHED"]
                    if topics
                    else ["AUTO_REVIEW_TOPIC_NOT_MATCHED"]
                )
                _ = self.event_repository.apply_auto_review_result(
                    event_id=event.id,
                    status=review_status,
                    tags=topics,
                    reasons=reasons,
                )
                _logger.info(
                    "Auto review event processed: task_id=%s event_id=%s event_key=%s status=%s tags=%s",
                    str(task.id),
                    str(event.id),
                    event.event_key,
                    review_status,
                    topics,
                )

                processed += 1
                if topics:
                    passed += 1
                else:
                    filtered += 1

            result: dict[str, object] = {
                "scanned": len(pending_events),
                "processed": processed,
                "passed": passed,
                "filtered": filtered,
                "llm_failed": llm_failed,
                "topics": list(self.TOPICS),
            }
            metrics: dict[str, object] = {
                "processed_rate": (processed / len(pending_events)) if pending_events else 0,
                "pass_rate": (passed / processed) if processed else 0,
            }
            _logger.info(
                "Auto review completed: task_id=%s scanned=%s processed=%s passed=%s filtered=%s llm_failed=%s",
                str(task.id),
                len(pending_events),
                processed,
                passed,
                filtered,
                llm_failed,
            )
            completed = self.task_repository.mark_completed(task.id, result=result, metrics=metrics)
            return self._to_task_response(completed or task)
        except Exception as exc:
            _logger.exception("Auto review task failed: task_id=%s", str(task.id))
            failed = self.task_repository.mark_failed(task.id, error_message=str(exc), max_attempts=3)
            return self._to_task_response(failed or task)

    def _validate_runtime_config(self) -> None:
        if not settings.auto_review_model.strip():
            raise ValueError("AUTO_REVIEW_MODEL is required")
        if not settings.auto_review_base_url.strip():
            raise ValueError("AUTO_REVIEW_BASE_URL is required")
        if not settings.auto_review_api_key.strip():
            raise ValueError("AUTO_REVIEW_API_KEY is required")

    def _classify_event_topics(self, event: EventEntity) -> list[str]:
        prompt = self._build_prompt(event)
        response = self.client.chat.completions.create(
            model=settings.auto_review_model,
            temperature=0,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "你是事件审核助手。只输出 JSON，不要输出解释。"
                        '格式必须是 {"topics": ["专题1", "专题2"]}。'
                    ),
                },
                {"role": "user", "content": prompt},
            ],
        )
        content = ""
        if response.choices:
            content = response.choices[0].message.content or ""
        return self._parse_topics(content)

    def _build_prompt(self, event: EventEntity) -> str:
        topics_text = "\n".join(f"- {item}" for item in self.TOPICS)
        title = (event.title or "")[:500]
        content = (event.content or "")[:4000]
        return (
            "请判断下面事件是否属于给定专题，可多选。\n"
            "仅可从给定专题中选择，不能自造标签。\n"
            "如果不属于任何专题，返回空数组。\n"
            "输出必须为 JSON 对象，格式：{\"topics\":[...]}。\n\n"
            f"专题列表:\n{topics_text}\n\n"
            f"事件标题: {title}\n"
            f"事件内容: {content}\n"
        )

    def _parse_topics(self, content: str) -> list[str]:
        cleaned = content.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.strip("`")
            cleaned = cleaned.replace("json", "", 1).strip()

        try:
            parsed_obj: object = json.loads(cleaned)
        except json.JSONDecodeError:
            return []

        candidates: list[str] = []
        if isinstance(parsed_obj, dict):
            value = parsed_obj.get("topics")
            if isinstance(value, list):
                candidates = [item for item in value if isinstance(item, str)]
        elif isinstance(parsed_obj, list):
            candidates = [item for item in parsed_obj if isinstance(item, str)]

        allowed = set(self.TOPICS)
        normalized: list[str] = []
        for item in candidates:
            topic = item.strip()
            if topic in allowed and topic not in normalized:
                normalized.append(topic)
        return normalized

    def _to_task_response(self, task: TaskExecutionEntity) -> S1TaskResponseModel:
        return S1TaskResponseModel(
            task_id=str(task.id),
            status=task.status,
            result=task.result or {},
        )
