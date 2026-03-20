import json
import logging
import time
from datetime import datetime, timedelta, timezone
from typing import cast
from uuid import UUID, uuid4

import requests
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
        self._nominatim_next_allowed_at: float = 0.0
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
            now = datetime.now(timezone.utc)
            range_start, range_end = self._resolve_question_time_range(now)
            batch_size = max(1, settings.auto_review_batch_size)

            scanned = self.question_repository.count_without_coordinates(
                range_start=range_start,
                range_end=range_end,
            )
            _logger.info(
                "Question location analysis started: task_id=%s force_run=%s scope=%s range_start=%s range_end=%s scanned=%s batch_size=%s osm_enabled=%s",
                str(task.id),
                force_run,
                settings.question_location_analysis_scope,
                range_start.isoformat() if range_start is not None else "all",
                range_end.isoformat() if range_end is not None else "all",
                scanned,
                batch_size,
                bool(settings.question_location_analysis_osm_base_url),
            )

            if settings.question_location_analysis_osm_base_url:
                area_scanned = self.question_repository.count_needing_area_backfill(
                    range_start=range_start,
                    range_end=range_end,
                )
                area_candidates = self.question_repository.list_needing_area_backfill(
                    range_start=range_start,
                    range_end=range_end,
                )
                self._validate_runtime_config(requires_llm=bool(area_candidates))
                area_phase = self._run_area_backfill_phase(
                    task_id=task.id,
                    candidates=area_candidates,
                    scanned=area_scanned,
                )

                coordinate_scanned = self.question_repository.count_needing_coordinate_backfill(
                    range_start=range_start,
                    range_end=range_end,
                )
                coordinate_candidates = self.question_repository.list_needing_coordinate_backfill(
                    range_start=range_start,
                    range_end=range_end,
                )
                coordinate_phase = self._run_coordinate_backfill_phase(
                    task_id=task.id,
                    candidates=coordinate_candidates,
                    scanned=coordinate_scanned,
                )

                area_processed = self._int_stat(area_phase, "processed")
                area_skipped = self._int_stat(area_phase, "skipped")
                area_failed = self._int_stat(area_phase, "failed")
                llm_failed = self._int_stat(area_phase, "llm_failed")
                area_updated = self._int_stat(area_phase, "updated")
                coordinate_processed = self._int_stat(coordinate_phase, "processed")
                coordinate_skipped = self._int_stat(coordinate_phase, "skipped")
                coordinate_failed = self._int_stat(coordinate_phase, "failed")
                coordinate_osm_failed = self._int_stat(coordinate_phase, "osm_failed")
                coordinates_updated = self._int_stat(coordinate_phase, "updated")
                processed = area_processed + coordinate_processed
                skipped = area_skipped + coordinate_skipped
                failed = area_failed + coordinate_failed
                failed_items = self._failed_items(area_phase) + self._failed_items(coordinate_phase)

                result = {
                    "mode": "osm_two_phase",
                    "scope": settings.question_location_analysis_scope,
                    "range_start": range_start.isoformat() if range_start is not None else None,
                    "range_end": range_end.isoformat() if range_end is not None else None,
                    "scanned": scanned,
                    "processed": processed,
                    "updated": coordinates_updated,
                    "area_updated": area_updated,
                    "coordinates_updated": coordinates_updated,
                    "skipped": skipped,
                    "failed": failed,
                    "llm_failed": llm_failed,
                    "osm_failed": coordinate_osm_failed,
                    "area_scanned": area_scanned,
                    "coordinate_scanned": coordinate_scanned,
                    "failed_items": failed_items,
                    "phases": {
                        "area_backfill": area_phase,
                        "coordinate_backfill": coordinate_phase,
                    },
                }
                metrics = {
                    "area_update_rate": (area_updated / area_processed) if area_processed else 0,
                    "coordinate_update_rate": (coordinates_updated / coordinate_processed)
                    if coordinate_processed
                    else 0,
                    "failure_rate": (failed / processed) if processed else 0,
                }
                _logger.info(
                    "Question location analysis completed: task_id=%s mode=osm_two_phase scanned=%s area_updated=%s coordinates_updated=%s failed=%s",
                    str(task.id),
                    scanned,
                    area_updated,
                    coordinates_updated,
                    failed,
                )
            else:
                candidates = self.question_repository.list_without_coordinates(
                    range_start=range_start,
                    range_end=range_end,
                )
                self._validate_runtime_config(requires_llm=bool(candidates))
                direct_phase = self._run_direct_coordinate_phase(
                    task_id=task.id,
                    candidates=candidates,
                    scanned=scanned,
                )
                direct_processed = self._int_stat(direct_phase, "processed")
                direct_updated = self._int_stat(direct_phase, "updated")
                direct_skipped = self._int_stat(direct_phase, "skipped")
                direct_failed = self._int_stat(direct_phase, "failed")
                direct_llm_failed = self._int_stat(direct_phase, "llm_failed")
                result = {
                    "mode": "llm_direct",
                    "scope": settings.question_location_analysis_scope,
                    "range_start": range_start.isoformat() if range_start is not None else None,
                    "range_end": range_end.isoformat() if range_end is not None else None,
                    "scanned": scanned,
                    "processed": direct_processed,
                    "updated": direct_updated,
                    "skipped": direct_skipped,
                    "failed": direct_failed,
                    "llm_failed": direct_llm_failed,
                    "failed_items": self._failed_items(direct_phase),
                }
                metrics = {
                    "update_rate": (direct_updated / direct_processed)
                    if direct_processed
                    else 0,
                    "failure_rate": (direct_failed / direct_processed)
                    if direct_processed
                    else 0,
                }
                _logger.info(
                    "Question location analysis completed: task_id=%s mode=llm_direct scanned=%s updated=%s failed=%s",
                    str(task.id),
                    scanned,
                    direct_updated,
                    direct_failed,
                )

            completed = self.task_repository.mark_completed(task.id, result=result, metrics=metrics)
            return self._to_task_response(completed or task)
        except Exception as exc:
            _logger.exception("Question location analysis task failed: task_id=%s", str(task.id))
            failed = self.task_repository.mark_failed(task.id, error_message=str(exc), max_attempts=3)
            return self._to_task_response(failed or task)

    def _validate_runtime_config(self, requires_llm: bool) -> None:
        if settings.question_location_analysis_osm_base_url and not requires_llm:
            return
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

    def _run_area_backfill_phase(
        self,
        task_id: UUID,
        candidates: list[dict[str, object]],
        scanned: int,
    ) -> dict[str, object]:
        processed = 0
        updated = 0
        skipped = 0
        failed = 0
        llm_failed = 0
        failed_items: list[dict[str, object]] = []
        _logger.info(
            "Question location area backfill started: task_id=%s scanned=%s",
            str(task_id),
            scanned,
        )

        for row in candidates:
            question_id, content, invalid_item = self._normalize_area_candidate(row)
            if invalid_item is not None:
                skipped += 1
                failed += 1
                failed_items.append(invalid_item)
                continue
            assert question_id is not None

            processed += 1
            _logger.info(
                "Question location area backfill processing: task_id=%s question_id=%s processed=%s/%s",
                str(task_id),
                str(question_id),
                processed,
                scanned,
            )

            try:
                location_name = self._extract_location_name_from_content(content)
            except Exception as exc:
                failed += 1
                llm_failed += 1
                failed_items.append({"question_id": str(question_id), "error": str(exc)})
                _logger.exception(
                    "Question location area extraction failed: task_id=%s question_id=%s",
                    str(task_id),
                    str(question_id),
                )
                continue

            if not location_name:
                failed += 1
                llm_failed += 1
                failed_items.append({"question_id": str(question_id), "error": "location_name_not_found"})
                _logger.info(
                    "Question location area not found: task_id=%s question_id=%s",
                    str(task_id),
                    str(question_id),
                )
                continue

            try:
                changed = self.question_repository.update_area_if_empty(
                    question_id=question_id,
                    area=location_name,
                )
            except Exception as exc:
                failed += 1
                failed_items.append({"question_id": str(question_id), "error": f"db_update_failed: {exc}"})
                _logger.exception(
                    "Question location area DB update failed: task_id=%s question_id=%s",
                    str(task_id),
                    str(question_id),
                )
                continue

            if changed:
                updated += 1
                _logger.info(
                    "Question location area updated: task_id=%s question_id=%s area=%s",
                    str(task_id),
                    str(question_id),
                    location_name,
                )
            else:
                skipped += 1
                _logger.info(
                    "Question location area skipped update: task_id=%s question_id=%s reason=already_set_or_missing",
                    str(task_id),
                    str(question_id),
                )

        return {
            "scanned": scanned,
            "processed": processed,
            "updated": updated,
            "skipped": skipped,
            "failed": failed,
            "llm_failed": llm_failed,
            "failed_items": failed_items,
        }

    def _run_coordinate_backfill_phase(
        self,
        task_id: UUID,
        candidates: list[dict[str, object]],
        scanned: int,
    ) -> dict[str, object]:
        processed = 0
        updated = 0
        skipped = 0
        failed = 0
        osm_failed = 0
        failed_items: list[dict[str, object]] = []
        _logger.info(
            "Question location coordinate backfill started: task_id=%s scanned=%s",
            str(task_id),
            scanned,
        )

        for row in candidates:
            question_id, area, invalid_item = self._normalize_coordinate_candidate(row)
            if invalid_item is not None:
                skipped += 1
                failed += 1
                failed_items.append(invalid_item)
                continue
            assert question_id is not None

            processed += 1
            _logger.info(
                "Question location coordinate backfill processing: task_id=%s question_id=%s processed=%s/%s",
                str(task_id),
                str(question_id),
                processed,
                scanned,
            )

            try:
                coordinates = self._extract_coordinates_osm_from_name(area)
            except Exception as exc:
                failed += 1
                osm_failed += 1
                failed_items.append({"question_id": str(question_id), "error": str(exc)})
                _logger.exception(
                    "Question location coordinate extraction failed: task_id=%s question_id=%s",
                    str(task_id),
                    str(question_id),
                )
                continue

            if coordinates is None:
                failed += 1
                osm_failed += 1
                failed_items.append({"question_id": str(question_id), "error": "coordinates_not_found"})
                _logger.info(
                    "Question location coordinates not found: task_id=%s question_id=%s area=%s",
                    str(task_id),
                    str(question_id),
                    area,
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
                failed_items.append({"question_id": str(question_id), "error": f"db_update_failed: {exc}"})
                _logger.exception(
                    "Question location coordinate DB update failed: task_id=%s question_id=%s",
                    str(task_id),
                    str(question_id),
                )
                continue

            if changed:
                updated += 1
                _logger.info(
                    "Question location coordinates updated: task_id=%s question_id=%s latitude=%s longitude=%s",
                    str(task_id),
                    str(question_id),
                    latitude,
                    longitude,
                )
            else:
                skipped += 1
                _logger.info(
                    "Question location coordinates skipped update: task_id=%s question_id=%s reason=already_set_or_missing",
                    str(task_id),
                    str(question_id),
                )

        return {
            "scanned": scanned,
            "processed": processed,
            "updated": updated,
            "skipped": skipped,
            "failed": failed,
            "osm_failed": osm_failed,
            "failed_items": failed_items,
        }

    def _run_direct_coordinate_phase(
        self,
        task_id: UUID,
        candidates: list[dict[str, object]],
        scanned: int,
    ) -> dict[str, object]:
        processed = 0
        updated = 0
        skipped = 0
        failed = 0
        llm_failed = 0
        failed_items: list[dict[str, object]] = []

        for row in candidates:
            question_id, area, content, invalid_item = self._normalize_direct_candidate(row)
            if invalid_item is not None:
                skipped += 1
                failed += 1
                failed_items.append(invalid_item)
                continue
            assert question_id is not None

            processed += 1
            _logger.info(
                "Question location processing: task_id=%s question_id=%s processed=%s/%s source=%s",
                str(task_id),
                str(question_id),
                processed,
                scanned,
                "area" if area else "content",
            )

            try:
                coordinates = self._extract_coordinates_from_llm(area if area else content)
            except Exception as exc:
                failed += 1
                llm_failed += 1
                failed_items.append({"question_id": str(question_id), "error": str(exc)})
                _logger.exception(
                    "Question location extraction failed: task_id=%s question_id=%s",
                    str(task_id),
                    str(question_id),
                )
                continue

            if coordinates is None:
                failed += 1
                llm_failed += 1
                failed_items.append({"question_id": str(question_id), "error": "coordinates_not_found"})
                _logger.info(
                    "Question location not found: task_id=%s question_id=%s source=%s",
                    str(task_id),
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
                failed_items.append({"question_id": str(question_id), "error": f"db_update_failed: {exc}"})
                _logger.exception(
                    "Question location DB update failed: task_id=%s question_id=%s",
                    str(task_id),
                    str(question_id),
                )
                continue

            if changed:
                updated += 1
                _logger.info(
                    "Question location updated: task_id=%s question_id=%s latitude=%s longitude=%s",
                    str(task_id),
                    str(question_id),
                    latitude,
                    longitude,
                )
            else:
                skipped += 1
                _logger.info(
                    "Question location skipped update: task_id=%s question_id=%s reason=already_set_or_missing",
                    str(task_id),
                    str(question_id),
                )

        return {
            "processed": processed,
            "updated": updated,
            "skipped": skipped,
            "failed": failed,
            "llm_failed": llm_failed,
            "failed_items": failed_items,
        }

    def _normalize_area_candidate(
        self, row: dict[str, object]
    ) -> tuple[UUID | None, str, dict[str, object] | None]:
        question_id_raw = row.get("id")
        if not isinstance(question_id_raw, UUID):
            _logger.error(
                "Question location area skipped due to invalid id type: question_id=%s",
                str(question_id_raw),
            )
            return None, "", {"question_id": str(question_id_raw), "error": "invalid question id type"}

        content_value = row.get("content")
        content = content_value.strip() if isinstance(content_value, str) else ""
        if not content:
            _logger.error(
                "Question location area failed: question_id=%s reason=empty_content",
                str(question_id_raw),
            )
            return question_id_raw, "", {"question_id": str(question_id_raw), "error": "content is empty"}

        return question_id_raw, content, None

    def _normalize_coordinate_candidate(
        self, row: dict[str, object]
    ) -> tuple[UUID | None, str, dict[str, object] | None]:
        question_id_raw = row.get("id")
        if not isinstance(question_id_raw, UUID):
            _logger.error(
                "Question location coordinates skipped due to invalid id type: question_id=%s",
                str(question_id_raw),
            )
            return None, "", {"question_id": str(question_id_raw), "error": "invalid question id type"}

        area_value = row.get("area")
        area = area_value.strip() if isinstance(area_value, str) else ""
        if not area:
            _logger.error(
                "Question location coordinates failed: question_id=%s reason=empty_area",
                str(question_id_raw),
            )
            return question_id_raw, "", {"question_id": str(question_id_raw), "error": "area is empty"}

        return question_id_raw, area, None

    def _normalize_direct_candidate(
        self, row: dict[str, object]
    ) -> tuple[UUID | None, str, str, dict[str, object] | None]:
        question_id_raw = row.get("id")
        if not isinstance(question_id_raw, UUID):
            _logger.error(
                "Question location skipped due to invalid id type: question_id=%s",
                str(question_id_raw),
            )
            return None, "", "", {"question_id": str(question_id_raw), "error": "invalid question id type"}

        area_value = row.get("area")
        content_value = row.get("content")
        area = area_value.strip() if isinstance(area_value, str) else ""
        content = content_value.strip() if isinstance(content_value, str) else ""
        if not area and not content:
            _logger.error(
                "Question location failed: question_id=%s reason=empty_input",
                str(question_id_raw),
            )
            return question_id_raw, area, content, {"question_id": str(question_id_raw), "error": "area and content are both empty"}

        return question_id_raw, area, content, None

    def _int_stat(self, stats: dict[str, object], key: str) -> int:
        value = stats.get(key, 0)
        return int(value) if isinstance(value, (int, float)) else 0

    def _failed_items(self, stats: dict[str, object]) -> list[dict[str, object]]:
        value = stats.get("failed_items", [])
        return value if isinstance(value, list) else []

    def _extract_coordinates_osm_from_name(self, location_name: str) -> tuple[float, float] | None:
        base_url = settings.question_location_analysis_osm_base_url.rstrip("/")
        timeout = settings.question_location_analysis_osm_timeout_seconds
        self._wait_for_nominatim_slot()
        params = {
            "q": location_name[:2000],
            "format": "json",
            "limit": 1,
            "addressdetails": 1,
        }
        headers = {
            "User-Agent": "MOPPA-LocationAnalysis/1.0 (backend-service)",
        }
        try:
            resp = requests.get(
                f"{base_url}/search",
                params=params,
                headers=headers,
                timeout=timeout,
            )
            if resp.status_code == 429:
                retry_after_text = resp.headers.get("Retry-After", "1")
                retry_after = self._to_float(retry_after_text)
                time.sleep(max(retry_after or 1.0, 1.0))
                self._wait_for_nominatim_slot()
                resp = requests.get(
                    f"{base_url}/search",
                    params=params,
                    headers=headers,
                    timeout=timeout,
                )
            resp.raise_for_status()
            results = resp.json()
        except Exception as exc:
            _logger.warning("OSM Nominatim request failed: location_name=%s error=%s", location_name[:200], exc)
            return None

        if not results or not isinstance(results, list):
            _logger.info("OSM Nominatim returned no results for: %s", location_name[:200])
            return None

        first = results[0]
        lat = self._to_float(first.get("lat"))
        lon = self._to_float(first.get("lon"))
        if lat is None or lon is None:
            _logger.info("OSM Nominatim returned invalid coords for: %s", location_name[:200])
            return None
        if lat < -90 or lat > 90 or lon < -180 or lon > 180:
            _logger.warning("OSM Nominatim returned out-of-range coords: lat=%s lon=%s", lat, lon)
            return None

        _logger.debug(
            "OSM resolved: location_name=%s lat=%s lon=%s display=%s",
            location_name[:100],
            lat,
            lon,
            first.get("display_name", "")[:100],
        )
        return lat, lon

    def _wait_for_nominatim_slot(self) -> None:
        now = time.monotonic()
        wait_seconds = self._nominatim_next_allowed_at - now
        if wait_seconds > 0:
            time.sleep(wait_seconds)
        self._nominatim_next_allowed_at = time.monotonic() + 1.1

    def _extract_coordinates_from_llm(self, text: str) -> tuple[float, float] | None:
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

    def _extract_location_name_from_content(self, content: str) -> str | None:
        prompt = (
            "请从以下文本中识别出最明确、最核心的地理位置名称（如城市、区县、乡镇、街道、景点等）。\n"
            "只返回地点名称，不要返回经纬度，不要返回解释，只返回一个 JSON 对象。\n"
            '输出格式：{"location_name": string, "confidence": string}。\n'
            "如果无法确定地点，返回 {\"location_name\": \"\", \"confidence\": \"low\"}。\n\n"
            f"文本：{content[:2000]}\n"
        )
        try:
            response = self.client.chat.completions.create(
                model=settings.auto_review_model,
                temperature=0,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "你是地址提取助手。只从用户文本中提取最核心的地点名称，"
                            "返回纯 JSON 对象，禁止 Markdown、代码块、前后缀。"
                            "只返回 location_name 和 confidence 两个字段。"
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
            )
            raw_content = ""
            if response.choices:
                raw_content = response.choices[0].message.content or ""
            parsed = self._parse_json_content(raw_content)
            if not isinstance(parsed, dict):
                return None
            payload = cast(dict[object, object], parsed)
            p: dict[str, object] = {str(k): v for k, v in payload.items()}
            location_name = p.get("location_name", "")
            confidence = str(p.get("confidence", "low"))
            if not isinstance(location_name, str) or not location_name.strip():
                _logger.info("LLM returned empty location_name for: %s", content[:100])
                return None
            if confidence == "low":
                _logger.info("LLM returned low confidence for: %s", content[:100])
                return None
            return location_name.strip()[:200]
        except Exception as exc:
            _logger.warning("Failed to extract location name from content: %s", exc)
            return None

    def _extract_coordinates(
        self, area: str, content: str
    ) -> tuple[tuple[float, float] | None, str | None]:
        coords = self._extract_coordinates_from_llm(area if area else content)
        return coords, None

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

    def _has_text(self, value: object) -> bool:
        return isinstance(value, str) and bool(value.strip())

    def _to_task_response(self, task: TaskExecutionEntity) -> S1TaskResponseModel:
        return S1TaskResponseModel(
            task_id=str(task.id),
            status=task.status,
            result=task.result or {},
        )
