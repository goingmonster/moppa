from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha1
from typing import cast

from openai import OpenAI

from app.config import settings
from app.integrations.tavily_search_client import TavilySearchResult
from app.models.s1_ingest_model import S1EventInputModel


_logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class TavilyReviewedEvent:
    index: int
    should_ingest: bool
    reason: str
    topic_match_score: int
    event: S1EventInputModel | None


class TavilyEventExtractionService:
    def __init__(self) -> None:
        self.client: OpenAI = OpenAI(
            api_key=settings.tavily_openai_api_key,
            base_url=settings.tavily_openai_base_url,
            timeout=settings.tavily_openai_timeout_seconds,
        )

    def review_events(self, *, topic: str, results: list[TavilySearchResult]) -> list[TavilyReviewedEvent]:
        if not results:
            _logger.info("Tavily extraction skipped: topic=%s reason=no_results", topic)
            return []

        batch_size = max(1, settings.tavily_openai_batch_size)
        _logger.info(
            "Tavily extraction started: topic=%s input_results=%s batch_size=%s",
            topic,
            len(results),
            batch_size,
        )
        items: list[TavilyReviewedEvent] = []
        for start in range(0, len(results), batch_size):
            batch = results[start:start + batch_size]
            sample_titles = [item.title for item in batch[:3] if item.title]
            _logger.info(
                "Tavily extraction batch started: topic=%s batch_start=%s batch_size=%s sample_titles=%s",
                topic,
                start,
                len(batch),
                sample_titles,
            )
            extracted = self._summarize_batch(topic=topic, results=batch)
            _logger.info(
                "Tavily extraction batch summarized: topic=%s batch_start=%s model_output_items=%s",
                topic,
                start,
                len(extracted),
            )
            extracted_by_index = {
                item["index"]: item
                for item in extracted
                if isinstance(item.get("index"), int)
            }
            for index, result in enumerate(batch, start=1):
                payload = extracted_by_index.get(index)
                review = self._build_reviewed_event(index=index, topic=topic, source=result, payload=payload)
                items.append(review)
            _logger.info(
                "Tavily extraction batch completed: topic=%s batch_start=%s reviewed_items=%s accepted_items=%s rejected_items=%s",
                topic,
                start,
                len(batch),
                len([item for item in items[-len(batch):] if item.should_ingest]),
                len([item for item in items[-len(batch):] if not item.should_ingest]),
            )
        _logger.info(
            "Tavily extraction completed: topic=%s input_results=%s reviewed_items=%s accepted_items=%s rejected_items=%s",
            topic,
            len(results),
            len(items),
            len([item for item in items if item.should_ingest]),
            len([item for item in items if not item.should_ingest]),
        )
        return items

    def _summarize_batch(self, *, topic: str, results: list[TavilySearchResult]) -> list[dict[str, object]]:
        prompt_payload: list[dict[str, object]] = []
        for index, item in enumerate(results, start=1):
            prompt_payload.append(
                {
                    "index": index,
                    "url": item.url,
                    "title": item.title,
                    "content": item.content,
                    "published_date": item.published_date,
                }
            )

        _logger.info(
            "Tavily OpenAI request: topic=%s model=%s items=%s",
            topic,
            settings.tavily_openai_model,
            len(results),
        )
        response = self.client.chat.completions.create(
            model=settings.tavily_openai_model,
            temperature=0,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "你是军事新闻事件审核与结构化助手。"
                        "你需要先判断一条新闻是否值得作为事件入库，再在通过时补全事件字段。"
                        "只能基于输入内容整理，不得补充未提供的事实。"
                        "以下情况 should_ingest=false：与专题不直接相关、主要是评论/分析/观点、缺少明确事件事实、明显重复转载且没有新增事实、内容过于模糊。"
                        "输出必须是 JSON 数组，每个元素格式为"
                        '{"index":1,"should_ingest":true,"reason":"...","topic_match_score":85,"title":"...","content":"...","event_time":"..."}。'
                        "如果 should_ingest=false，则 title/content/event_time 可为空字符串。topic_match_score 为 0-100 的整数。"
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"专题：{topic}\n"
                        "请逐条判断下面新闻是否应入库为 event。"
                        "若应入库，请生成适合 event 表的 title/content/event_time；content 用简体中文，保留事实，不要编造。"
                        "若不应入库，请仅给出 should_ingest=false、reason 和 topic_match_score。"
                        f"\n\n输入数据：\n{json.dumps(prompt_payload, ensure_ascii=False)}"
                    ),
                },
            ],
        )
        content = ""
        if response.choices:
            content = response.choices[0].message.content or ""
        parsed = self._parse_items(content)
        _logger.info(
            "Tavily OpenAI response parsed: topic=%s items=%s raw_chars=%s",
            topic,
            len(parsed),
            len(content),
        )
        return parsed

    def _parse_items(self, content: str) -> list[dict[str, object]]:
        cleaned = content.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.strip("`")
            cleaned = cleaned.replace("json", "", 1).strip()

        start = cleaned.find("[")
        end = cleaned.rfind("]")
        if start >= 0 and end >= start:
            cleaned = cleaned[start:end + 1]

        try:
            parsed_obj = cast(object, json.loads(cleaned))
        except json.JSONDecodeError:
            _logger.warning(
                "Tavily OpenAI response parse failed: raw_chars=%s preview=%s",
                len(content),
                content[:300],
            )
            return []
        if not isinstance(parsed_obj, list):
            _logger.warning(
                "Tavily OpenAI response shape invalid: expected=list actual=%s preview=%s",
                type(parsed_obj).__name__,
                cleaned[:300],
            )
            return []
        parsed = cast(list[object], parsed_obj)
        return [cast(dict[str, object], item) for item in parsed if isinstance(item, dict)]

    def _build_reviewed_event(
        self,
        *,
        index: int,
        topic: str,
        source: TavilySearchResult,
        payload: dict[str, object] | None,
    ) -> TavilyReviewedEvent:
        should_ingest = self._bool_value(payload.get("should_ingest") if payload else None)
        reason = str(payload.get("reason") or "") if payload else ""
        topic_match_score = self._score_value(payload.get("topic_match_score") if payload else None)

        if not should_ingest:
            return TavilyReviewedEvent(
                index=index,
                should_ingest=False,
                reason=reason.strip() or "模型判断不符合入库条件",
                topic_match_score=topic_match_score,
                event=None,
            )

        title = str(payload.get("title") or source.title or "未命名事件").strip() if payload else (source.title or "未命名事件")
        summary = str(payload.get("content") or "").strip() if payload else ""
        if not summary:
            summary = source.content.strip() or source.title.strip() or source.url.strip()
        content = self._build_content(topic=topic, source=source, summary=summary)
        event_time = self._resolve_event_time(str(payload.get("event_time") or "").strip() if payload else None, source.published_date)
        event = S1EventInputModel(
            event_key=self._build_event_key(topic=topic, url=source.url, title=title, published_date=source.published_date),
            title=title[:255] or "未命名事件",
            content=content,
            source_system="tavily",
            credibility_level=3,
            event_time=event_time,
            url=source.url or None,
        )
        return TavilyReviewedEvent(
            index=index,
            should_ingest=True,
            reason=reason.strip() or "符合专题且具备明确事件事实",
            topic_match_score=topic_match_score,
            event=event,
        )

    def _build_content(self, *, topic: str, source: TavilySearchResult, summary: str) -> str:
        parts = [
            f"来源标题：{source.title}" if source.title else "",
            f"摘要：{summary}",
            f"原始链接：{source.url}" if source.url else "",
            f"专题：{topic}"
        ]
        return "\n".join(part for part in parts if part)

    def _resolve_event_time(self, model_event_time: str | None, published_date: str | None) -> datetime:
        for candidate in [model_event_time, published_date]:
            if not candidate:
                continue
            normalized = candidate.strip().replace("Z", "+00:00")
            try:
                parsed = datetime.fromisoformat(normalized)
                if parsed.tzinfo is None:
                    return parsed.replace(tzinfo=timezone.utc)
                return parsed
            except ValueError:
                pass
        return datetime.now(timezone.utc)

    def _build_event_key(self, *, topic: str, url: str, title: str, published_date: str | None) -> str:
        base = url.strip() or f"{topic}|{title.strip()}|{published_date or ''}"
        digest = sha1(base.encode("utf-8")).hexdigest()
        return f"tavily:{digest}"

    def _bool_value(self, value: object) -> bool:
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.strip().lower() in {"true", "1", "yes"}
        if isinstance(value, (int, float)):
            return value != 0
        return False

    def _score_value(self, value: object) -> int:
        if isinstance(value, int):
            return max(0, min(value, 100))
        if isinstance(value, float):
            return max(0, min(int(value), 100))
        if isinstance(value, str):
            try:
                parsed = int(value.strip())
            except ValueError:
                return 0
            return max(0, min(parsed, 100))
        return 0
