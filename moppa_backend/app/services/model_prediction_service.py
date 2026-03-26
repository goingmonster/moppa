import json
import logging
import re
import time
from datetime import datetime, timedelta, timezone
from typing import cast
from uuid import UUID, uuid4

from openai import OpenAI
from sqlalchemy.orm import Session

from app.config.settings import settings
from app.db.models import TaskExecutionEntity
from app.models.prediction_model import PredictionItemModel
from app.models.s1_ingest_model import S1TaskResponseModel
from app.repositories.model_endpoint_repository import ModelEndpointRepository
from app.repositories.prediction_repository import PredictionRepository
from app.repositories.question_repository import QuestionRepository
from app.repositories.task_execution_repository import TaskExecutionRepository

_logger = logging.getLogger(__name__)


def _parse_answer_options(answer_space: str) -> list[dict[str, str]]:
    """Parse answer_space into a list of {key, label} dicts.

    Supports JSON arrays, JSON objects, and newline-separated text.
    """
    trimmed = (answer_space or "").strip()
    if not trimmed:
        return []

    normalized: list[dict[str, str]] = []
    starts_with_json = trimmed.startswith("{") or trimmed.startswith("[")

    if starts_with_json:
        try:
            parsed = json.loads(trimmed)
        except json.JSONDecodeError:
            parsed = None

        if isinstance(parsed, list):
            for idx, item in enumerate(parsed):
                label = str(item).strip() if item is not None else ""
                if label:
                    normalized.append({"key": str(idx + 1), "label": label})
        elif isinstance(parsed, dict):
            for key, value in parsed.items():
                label = str(value).strip() if value is not None else ""
                if label:
                    normalized.append({"key": key.strip() or str(len(normalized) + 1), "label": label})

    if not normalized and not starts_with_json:
        for idx, line in enumerate(trimmed.splitlines()):
            label = line.strip()
            if label:
                normalized.append({"key": str(idx + 1), "label": label})

    return normalized


def _extract_confidence(text: str) -> float | None:
    """Try to extract a confidence value (0-100) from model output."""
    patterns = [
        r"(?:置信度|confidence)\s*[:：]\s*(\d+(?:\.\d+)?)\s*%?",
        r"(\d+(?:\.\d+)?)\s*%\s*(?:置信|确信|信心)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            value = float(match.group(1))
            return min(max(value, 0.0), 100.0)
    return None


class ModelPredictionService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.task_repository = TaskExecutionRepository(db)
        self.prediction_repository = PredictionRepository(db)
        self.endpoint_repository = ModelEndpointRepository(db)
        self.question_repository = QuestionRepository(db)

    def run_prediction_job(self, force_run: bool = False) -> S1TaskResponseModel:
        now = datetime.now(timezone.utc)
        date_window = now.replace(hour=0, minute=0, second=0, microsecond=0)
        run_mode = "manual" if force_run else "scheduled"
        range_start, range_end = self._resolve_question_time_range(now)

        if force_run:
            idempotency_key = f"model_prediction:manual:{now.isoformat()}:{uuid4()}"
            existing = None
        else:
            idempotency_key = f"model_prediction:{date_window.isoformat()}"
            existing = self.task_repository.get_by_idempotency_key(idempotency_key)
            if existing is not None and existing.status in {"running", "completed"}:
                _logger.info(
                    "Model prediction skipped by idempotency: mode=%s existing_task_id=%s status=%s idempotency_key=%s",
                    run_mode,
                    str(existing.id),
                    existing.status,
                    idempotency_key,
                )
                return self._to_task_response(existing)

        task = existing
        if task is None:
            task = self.task_repository.create_pending(
                task_type="model_prediction",
                idempotency_key=idempotency_key,
                trace_id=uuid4(),
                business_id=None,
                date_window=date_window,
            )
            _logger.info(
                "Model prediction task created: mode=%s task_id=%s idempotency_key=%s date_window=%s",
                run_mode,
                str(task.id),
                idempotency_key,
                date_window.isoformat(),
            )
        self.task_repository.mark_running(task.id)
        _logger.info("Model prediction task running: mode=%s task_id=%s", run_mode, str(task.id))

        try:
            models = self.endpoint_repository.list_active()
            if not models:
                _logger.warning(
                    "Model prediction ended early: mode=%s task_id=%s reason=no_active_models",
                    run_mode,
                    str(task.id),
                )
                self.task_repository.mark_completed(
                    task.id,
                    result={"message": "No active model endpoints found"},
                    metrics={"models": 0, "questions": 0, "predictions": 0},
                )
                return self._to_task_response(task)

            questions = self.question_repository.list_published_by_date_range(range_start, range_end, now)

            _logger.info(
                "Model prediction started: mode=%s task_id=%s force_run=%s scope=%s question_filter=non_expired models=%s questions=%s date_range=%s~%s",
                run_mode,
                str(task.id),
                force_run,
                settings.model_prediction_event_scope,
                len(models),
                len(questions),
                range_start.isoformat() if range_start is not None else "ALL",
                range_end.isoformat() if range_end is not None else "ALL",
            )

            total_predictions = 0
            completed_predictions = 0
            failed_predictions = 0
            skipped_predictions = 0
            total_inference_ms = 0
            total_tokens = 0

            for model in models:
                model_id = UUID(str(model["id"]))
                model_name = str(model["model_name"])
                model_identifier = str(model.get("identifier", ""))
                endpoint_url = str(model["endpoint_url"])
                api_key_ref = str(model["api_key_ref"]) if model.get("api_key_ref") is not None else None
                max_tokens = int(cast(int, model["max_tokens"]))
                temperature = float(cast(float, model["temperature"]))
                timeout_seconds = int(cast(int, model["timeout_seconds"]))
                model_completed = 0
                model_failed = 0
                model_skipped = 0

                _logger.info(
                    "Model prediction model-start: task_id=%s model_id=%s model_identifier=%s model_name=%s timeout=%s max_tokens=%s temperature=%s",
                    str(task.id),
                    str(model_id),
                    model_identifier,
                    model_name,
                    timeout_seconds,
                    max_tokens,
                    temperature,
                )

                if not api_key_ref:
                    _logger.warning(
                        "Model prediction model-skipped: task_id=%s model=%s id=%s reason=no_api_key_ref",
                        str(task.id),
                        model_name,
                        str(model_id),
                    )
                    continue

                client = OpenAI(
                    api_key=api_key_ref,
                    base_url=endpoint_url,
                    timeout=timeout_seconds,
                )

                for question in questions:
                    question_id = UUID(str(question["id"]))
                    level = int(cast(int, question["level"]))

                    try:
                        existing_pred = self.prediction_repository.get_existing(question_id, model_id)
                        if existing_pred is not None:
                            skipped_predictions += 1
                            model_skipped += 1
                            _logger.info(
                                "Model prediction question-skipped: task_id=%s model=%s question_id=%s reason=already_exists",
                                str(task.id),
                                model_name,
                                str(question_id),
                            )
                            continue

                        start_time = time.perf_counter()

                        prompt = self._build_prompt(
                            content=str(question.get("content", "")),
                            background=str(question.get("background", "")),
                            answer_space=str(question.get("answer_space", "")),
                            level=level,
                        )

                        response = client.chat.completions.create(
                            model=model_name,
                            temperature=temperature,
                            max_tokens=max_tokens,
                            messages=[
                                {"role": "system", "content": self._system_prompt(level)},
                                {"role": "user", "content": prompt},
                            ],
                        )

                        inference_time_ms = int((time.perf_counter() - start_time) * 1000)

                        answer = ""
                        if response.choices:
                            answer = response.choices[0].message.content or ""

                        usage: dict[str, object] = {}
                        if response.usage:
                            usage = {
                                "prompt_tokens": response.usage.prompt_tokens or 0,
                                "completion_tokens": response.usage.completion_tokens or 0,
                                "total_tokens": response.usage.total_tokens or 0,
                            }

                        confidence = _extract_confidence(answer)

                        self.prediction_repository.upsert(
                            question_id=question_id,
                            model_id=model_id,
                            prediction_content=answer.strip(),
                            confidence=confidence,
                            inference_time_ms=inference_time_ms,
                            token_usage=usage,
                            trace_id=uuid4(),
                            task_execution_id=task.id,
                            status="completed",
                        )

                        completed_predictions += 1
                        model_completed += 1
                        total_predictions += 1
                        total_inference_ms += inference_time_ms
                        total_tokens += cast(int, usage.get("total_tokens", 0))
                        _logger.info(
                            "Model prediction question-completed: task_id=%s model=%s question_id=%s level=%s inference_ms=%s total_tokens=%s confidence=%s",
                            str(task.id),
                            model_name,
                            str(question_id),
                            level,
                            inference_time_ms,
                            usage.get("total_tokens", 0),
                            confidence,
                        )

                    except Exception:
                        failed_predictions += 1
                        model_failed += 1
                        total_predictions += 1
                        error_msg = f"model={model_name} question={question_id}: prediction failed"
                        _logger.exception(
                            "Model prediction failed: task_id=%s %s",
                            str(task.id),
                            error_msg,
                        )
                        try:
                            self.prediction_repository.upsert(
                                question_id=question_id,
                                model_id=model_id,
                                prediction_content="",
                                confidence=None,
                                inference_time_ms=None,
                                token_usage={},
                                trace_id=uuid4(),
                                task_execution_id=task.id,
                                status="failed",
                                error_message=error_msg,
                            )
                        except Exception:
                            _logger.exception(
                                "Failed to write failed prediction record: question_id=%s model_id=%s",
                                str(question_id),
                                str(model_id),
                            )

                _logger.info(
                    "Model prediction model-end: task_id=%s model=%s completed=%s failed=%s skipped=%s",
                    str(task.id),
                    model_name,
                    model_completed,
                    model_failed,
                    model_skipped,
                )

            result: dict[str, object] = {
                "models": len(models),
                "questions": len(questions),
                "total_attempts": total_predictions,
                "completed": completed_predictions,
                "failed": failed_predictions,
                "skipped": skipped_predictions,
            }
            metrics: dict[str, object] = {
                "success_rate": (completed_predictions / total_predictions) if total_predictions else 0,
                "avg_inference_ms": (total_inference_ms / completed_predictions) if completed_predictions else 0,
                "total_tokens": total_tokens,
            }

            _logger.info(
                "Model prediction completed: mode=%s task_id=%s models=%s questions=%s "
                "completed=%s failed=%s skipped=%s",
                run_mode,
                str(task.id),
                len(models),
                len(questions),
                completed_predictions,
                failed_predictions,
                skipped_predictions,
            )

            completed_task = self.task_repository.mark_completed(task.id, result=result, metrics=metrics)
            return self._to_task_response(completed_task or task)

        except Exception as exc:
            _logger.exception("Model prediction task failed: mode=%s task_id=%s", run_mode, str(task.id))
            failed_task = self.task_repository.mark_failed(task.id, error_message=str(exc), max_attempts=3)
            return self._to_task_response(failed_task or task)

    def list_by_question(self, question_id: str) -> list[PredictionItemModel]:
        rows = self.prediction_repository.list_by_question(UUID(question_id))
        items: list[PredictionItemModel] = []
        for row in rows:
            created_at_raw = row.get("created_at")
            submission_time_raw = row.get("submission_time")
            token_usage_raw = row.get("token_usage")
            items.append(
                PredictionItemModel(
                    id=str(row["id"]),
                    question_id=str(row["question_id"]),
                    model_id=str(row["model_id"]),
                    model_name=str(row.get("model_name", "")),
                    model_identifier=str(row.get("model_identifier", "")),
                    prediction_content=str(row["prediction_content"]),
                    confidence=float(cast(float, row["confidence"])) if row.get("confidence") is not None else None,
                    inference_time_ms=int(cast(int, row["inference_time_ms"])) if row.get("inference_time_ms") is not None else None,
                    token_usage=dict(token_usage_raw) if isinstance(token_usage_raw, dict) else {},
                    status=str(row["status"]),
                    error_message=str(row["error_message"]) if row.get("error_message") else None,
                    submission_time=submission_time_raw.isoformat() if isinstance(submission_time_raw, datetime) else "",
                    created_at=created_at_raw.isoformat() if isinstance(created_at_raw, datetime) else "",
                )
            )
        return items

    @staticmethod
    def _system_prompt(level: int) -> str:
        if level <= 2:
            return (
                "你是一个预测分析助手。请根据提供的背景信息和可选答案范围给出你的预测。\n"
                "你的回答必须是可选答案范围内的一个或多个选项。\n"
                "请只输出选项内容本身，不要输出多余的解释或分析。\n"
                "如果是多选题，请用逗号分隔多个选项。\n"
            )
        return (
            "你是一个预测分析助手。请根据提供的背景信息给出你的预测回答。\n"
            "请给出尽可能准确和有依据的预测。\n"
            "可以直接给出你的预测结论。\n"
        )

    @staticmethod
    def _build_prompt(content: str, background: str, answer_space: str, level: int) -> str:
        parts: list[str] = []

        if level <= 2:
            options = _parse_answer_options(answer_space)
            parts.append("请从以下可选答案中选择你的预测：")
            for opt in options:
                parts.append(f"  {opt['key']}. {opt['label']}")
            if not options and answer_space.strip():
                parts.append(f"答案范围：{answer_space.strip()}")
        else:
            if answer_space.strip():
                parts.append(f"参考答案范围：{answer_space.strip()}")

        if background and background.strip():
            parts.append(f"\n背景信息：\n{background.strip()}")

        parts.append(f"\n问题：\n{content.strip()}")

        return "\n".join(parts)

    @staticmethod
    def _resolve_question_time_range(now: datetime) -> tuple[datetime | None, datetime | None]:
        scope = settings.model_prediction_event_scope
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

    @staticmethod
    def _to_task_response(task: TaskExecutionEntity) -> S1TaskResponseModel:
        return S1TaskResponseModel(
            task_id=str(task.id),
            status=task.status,
            result=task.result or {},
        )
