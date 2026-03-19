import json
import logging
from datetime import datetime, timedelta, timezone
from typing import cast
from uuid import UUID, uuid4

from openai import OpenAI
from sqlalchemy.orm import Session

from app.config import settings
from app.db.models import TaskExecutionEntity
from app.models.s1_ingest_model import S1TaskResponseModel
from app.repositories.question_repository import QuestionRepository
from app.repositories.task_execution_repository import TaskExecutionRepository


_logger = logging.getLogger(__name__)


class QuestionLocationAnalysisService:
    def __init__(self, db: Session) -> None:
        self.db: Session = db
        self.question_repository: QuestionRepository = QuestionRepository(db)
        self.task_repository: TaskExecutionRepository = TaskExecutionRepository(db)
        self.client: OpenAI = OpenAI(
            api_key=settings.auto_review_api_key,
            base_url=settings.auto_review_base_url,
            timeout=settings.auto_review_timeout_seconds,
        )

    def run_location_analysis_job(self, force_run: bool = False) -> S1TaskResponseModel:
        date_window = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
        if force_run:
            idempotency_key = (
                f"question_location_analysis:manual:{datetime.now(timezone.utc).isoformat()}:{uuid4()}"
            )
            existing = None
        else:
            idempotency_key = f"question_location_analysis:{date_window.isoformat()}"
            existing = self.task_repository.get_by_idempotency_key(idempotency_key)
            if existing is not None and existing.status in {"running", "completed"}:
                return self._to_task_response(existing)

        task = existing
        if task is None:
            task = self.task_repository.create_pending(
                task_type="question_location_analysis",
                idempotency_key=idempotency_key,
                trace_id=uuid4(),
                business_id=None,
                date_window=date_window,
            )
        _ = self.task_repository.mark_running(task.id)

        try:
            self._validate_runtime_config()
            now = datetime.now(timezone.utc)
            range_start, range_end = self._resolve_question_time_range(now)
            batch_size = max(1, settings.auto_review_batch_size)

            scanned = self.question_repository.count_without_coordinates(
                range_start=range_start,
                range_end=range_end,
            )
            _logger.info(
                "Question location analysis started: task_id=%s force_run=%s scope=%s range_start=%s range_end=%s scanned=%s batch_size=%s",
                str(task.id),
                force_run,
                settings.question_location_analysis_scope,
                range_start.isoformat() if range_start is not None else "all",
                range_end.isoformat() if range_end is not None else "all",
                scanned,
                batch_size,
            )

            processed = 0
            updated = 0
            skipped = 0
            failed = 0
            llm_failed = 0
            failed_items: list[dict[str, object]] = []
            candidates = self.question_repository.list_without_coordinates(
                range_start=range_start,
                range_end=range_end,
            )

            for row in candidates:
                question_id_raw = row.get("id")
                if not isinstance(question_id_raw, UUID):
                    skipped += 1
                    failed += 1
                    failed_items.append(
                        {
                            "question_id": str(question_id_raw),
                            "error": "invalid question id type",
                        }
                    )
                    _logger.error(
                        "Question location skipped due to invalid id type: task_id=%s question_id=%s",
                        str(task.id),
                        str(question_id_raw),
                    )
                    continue

                question_id = question_id_raw
                area_value = row.get("area")
                content_value = row.get("content")
                area = area_value.strip() if isinstance(area_value, str) else ""
                content = content_value.strip() if isinstance(content_value, str) else ""
                target_text = area if area else content

                processed += 1
                _logger.info(
                    "Question location processing: task_id=%s question_id=%s processed=%s/%s source=%s",
                    str(task.id),
                    str(question_id),
                    processed,
                    scanned,
                    "area" if area else "content",
                )

                if not target_text:
                    skipped += 1
                    failed += 1
                    failed_items.append(
                        {
                            "question_id": str(question_id),
                            "error": "area and content are both empty",
                        }
                    )
                    _logger.error(
                        "Question location failed: task_id=%s question_id=%s reason=empty_input",
                        str(task.id),
                        str(question_id),
                    )
                    continue

                try:
                    coordinates = self._extract_coordinates(target_text)
                except Exception as exc:
                    failed += 1
                    llm_failed += 1
                    failed_items.append(
                        {
                            "question_id": str(question_id),
                            "error": str(exc),
                        }
                    )
                    _logger.exception(
                        "Question location extraction failed: task_id=%s question_id=%s",
                        str(task.id),
                        str(question_id),
                    )
                    continue

                if coordinates is None:
                    failed += 1
                    llm_failed += 1
                    failed_items.append(
                        {
                            "question_id": str(question_id),
                            "error": "coordinates_not_found",
                        }
                    )
                    _logger.info(
                        "Question location not found: task_id=%s question_id=%s source=%s",
                        str(task.id),
                        str(question_id),
                        "area" if area else "content",
                    )
                    continue

                latitude, longitude = coordinates

                try:
                    changed = self.question_repository.update_coordinates(
                        question_id=question_id,
                        latitude=latitude,
                        longitude=longitude,
                    )
                except Exception as exc:
                    failed += 1
                    failed_items.append(
                        {
                            "question_id": str(question_id),
                            "error": f"db_update_failed: {exc}",
                        }
                    )
                    _logger.exception(
                        "Question location DB update failed: task_id=%s question_id=%s",
                        str(task.id),
                        str(question_id),
                    )
                    continue

                if changed:
                    updated += 1
                    _logger.info(
                        "Question location updated: task_id=%s question_id=%s latitude=%s longitude=%s",
                        str(task.id),
                        str(question_id),
                        latitude,
                        longitude,
                    )
                else:
                    skipped += 1
                    _logger.info(
                        "Question location skipped update: task_id=%s question_id=%s reason=already_set_or_missing",
                        str(task.id),
                        str(question_id),
                    )

            result: dict[str, object] = {
                "scope": settings.question_location_analysis_scope,
                "range_start": range_start.isoformat() if range_start is not None else None,
                "range_end": range_end.isoformat() if range_end is not None else None,
                "scanned": scanned,
                "processed": processed,
                "updated": updated,
                "skipped": skipped,
                "failed": failed,
                "llm_failed": llm_failed,
                "failed_items": failed_items,
            }
            metrics: dict[str, object] = {
                "update_rate": (updated / processed) if processed else 0,
                "failure_rate": (failed / processed) if processed else 0,
            }
            _logger.info(
                "Question location analysis completed: task_id=%s scanned=%s processed=%s updated=%s skipped=%s failed=%s llm_failed=%s",
                str(task.id),
                scanned,
                processed,
                updated,
                skipped,
                failed,
                llm_failed,
            )
            completed = self.task_repository.mark_completed(task.id, result=result, metrics=metrics)
            return self._to_task_response(completed or task)
        except Exception as exc:
            _logger.exception("Question location analysis task failed: task_id=%s", str(task.id))
            failed = self.task_repository.mark_failed(task.id, error_message=str(exc), max_attempts=3)
            return self._to_task_response(failed or task)

    def _validate_runtime_config(self) -> None:
        if not settings.auto_review_model.strip():
            raise ValueError("AUTO_REVIEW_MODEL is required")
        if not settings.auto_review_base_url.strip():
            raise ValueError("AUTO_REVIEW_BASE_URL is required")
        if not settings.auto_review_api_key.strip():
            raise ValueError("AUTO_REVIEW_API_KEY is required")

    def _resolve_question_time_range(self, now: datetime) -> tuple[datetime | None, datetime | None]:
        scope = settings.question_location_analysis_scope
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

    def _extract_coordinates(self, text: str) -> tuple[float, float] | None:
        prompt = self._build_prompt(text)
        response = self.client.chat.completions.create(
            model=settings.auto_review_model,
            temperature=0,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "你是地理坐标提取助手。你的任务是根据文本定位最可能的地理位置，并返回该位置的经纬度。"
                        "只能输出一个 JSON 对象，禁止输出 Markdown、代码块、解释、前后缀文本。"
                        '输出格式必须严格为 {"latitude": number|null, "longitude": number|null, "location_name": string, "confidence": string}。'
                        "如果无法从文本中 reasonably 确定到城市、区县、乡镇、街道、景点或明确行政区域，"
                        '必须返回 {"latitude": null, "longitude": null, "location_name": "", "confidence": "low"}。'
                        "不要编造坐标，不要返回数组，不要返回嵌套对象，不要使用中文键名。"
                    ),
                },
                {"role": "user", "content": prompt},
            ],
        )
        content = ""
        if response.choices:
            content = response.choices[0].message.content or ""
        return self._parse_coordinates(content)

    def _build_prompt(self, input_text: str) -> str:
        cleaned = input_text[:2000]
        return (
            "请识别下面文本中最明确、最核心的地理位置，并返回该位置的标准经纬度。\n"
            "优先识别顺序：具体地点/景点 > 街道/乡镇 > 区县 > 城市 > 省份 > 国家。\n"
            "如果文本里出现多个地点，选择最主要、最直接相关的一个地点。\n"
            "如果只有模糊描述、没有足够信息确定到可落点的位置，返回 null 坐标，不要猜测。\n"
            "必须只返回一个 JSON 对象，字段固定为 latitude、longitude、location_name、confidence。\n"
            '示例1：{"latitude": 39.9042, "longitude": 116.4074, "location_name": "北京市", "confidence": "high"}\n'
            '示例2：{"latitude": null, "longitude": null, "location_name": "", "confidence": "low"}\n\n'
            f"文本：{cleaned}\n"
        )

    def _parse_coordinates(self, raw_content: str) -> tuple[float, float] | None:
        parsed_obj = self._parse_json_content(raw_content)
        if not isinstance(parsed_obj, dict):
            raise ValueError("LLM response is not a JSON object")
        raw_payload = cast(dict[object, object], parsed_obj)
        payload: dict[str, object] = {str(key): value for key, value in raw_payload.items()}

        latitude = self._to_float(payload.get("latitude"), payload.get("lat"))
        longitude = self._to_float(
            payload.get("longitude"),
            payload.get("lng"),
            payload.get("lon"),
        )
        if latitude is None or longitude is None:
            _logger.info(
                "Question location model returned no coordinates: response=%s",
                raw_content[:500],
            )
            return None
        if latitude < -90 or latitude > 90:
            raise ValueError(f"latitude out of range: {latitude}")
        if longitude < -180 or longitude > 180:
            raise ValueError(f"longitude out of range: {longitude}")
        return latitude, longitude

    def _parse_json_content(self, content: str) -> object:
        cleaned = content.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.strip("`")
            cleaned = cleaned.replace("json", "", 1).strip()

        try:
            parsed = cast(object, json.loads(cleaned))
            return parsed
        except json.JSONDecodeError:
            pass

        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start >= 0 and end > start:
            candidate = cleaned[start : end + 1]
            try:
                parsed_candidate = cast(object, json.loads(candidate))
                return parsed_candidate
            except json.JSONDecodeError as exc:
                raise ValueError(f"invalid JSON content: {cleaned[:500]}") from exc

        raise ValueError(f"invalid JSON content: {cleaned[:500]}")

    def _to_float(self, *values: object) -> float | None:
        for value in values:
            if value is None:
                continue
            if isinstance(value, (int, float)):
                return float(value)
            if isinstance(value, str):
                text = value.strip()
                if not text:
                    continue
                try:
                    return float(text)
                except ValueError:
                    continue
        return None

    def _to_task_response(self, task: TaskExecutionEntity) -> S1TaskResponseModel:
        return S1TaskResponseModel(
            task_id=str(task.id),
            status=task.status,
            result=task.result or {},
        )
