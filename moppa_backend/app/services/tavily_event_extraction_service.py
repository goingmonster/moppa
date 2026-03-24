from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from hashlib import sha1
from typing import cast

from openai import OpenAI

from app.config import settings
from app.integrations.tavily_search_client import TavilySearchResult
from app.models.s1_ingest_model import S1EventInputModel


_logger = logging.getLogger(__name__)


class TavilyEventExtractionService:
    def __init__(self) -> None:
        self.client: OpenAI = OpenAI(
            api_key=settings.tavily_openai_api_key,
            base_url=settings.tavily_openai_base_url,
            timeout=settings.tavily_openai_timeout_seconds,
        )

    def build_events(self, *, topic: str, results: list[TavilySearchResult]) -> list[S1EventInputModel]:
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
        items: list[S1EventInputModel] = []
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
                title = str(payload.get("title") or result.title or "未命名事件").strip() if payload else (result.title or "未命名事件")
                content = str(payload.get("content") or "").strip() if payload else ""
                if not content:
                    base_content = result.content.strip() or result.title.strip() or result.url.strip()
                    content = base_content
                content = self._build_content(topic=topic, source=result, summary=content)
                event_time = self._resolve_event_time(result.published_date)
                items.append(
                    S1EventInputModel(
                        event_key=self._build_event_key(topic=topic, url=result.url, title=title, published_date=result.published_date),
                        title=title[:255] or "未命名事件",
                        content=content,
                        source_system="tavily",
                        credibility_level=3,
                        event_time=event_time,
                        url=result.url or None,
                    )
                )
            _logger.info(
                "Tavily extraction batch completed: topic=%s batch_start=%s generated_events=%s",
                topic,
                start,
                len(batch),
            )
        _logger.info(
            "Tavily extraction completed: topic=%s input_results=%s generated_events=%s",
            topic,
            len(results),
            len(items),
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
                        "你是军事新闻事件整理助手。"
                        "只能基于输入内容整理，不得补充未提供的事实。"
                        "输出必须是 JSON 数组，每个元素格式为"
                        '{"index":1,"title":"...","content":"..."}。'
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"专题：{topic}\n"
                        "请为下面每条新闻生成适合 event 表入库的标题和内容摘要。"
                        "content 用简体中文，保留事实，不要编造。内容丰富度适中，避免过于简短。"
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

    def _build_content(self, *, topic: str, source: TavilySearchResult, summary: str) -> str:
        parts = [
            f"来源标题：{source.title}" if source.title else "",
            f"摘要：{summary}",
            f"原始链接：{source.url}" if source.url else "",
            f"专题：{topic}"
        ]
        return "\n".join(part for part in parts if part)

    def _resolve_event_time(self, published_date: str | None) -> datetime:
        if published_date:
            normalized = published_date.strip().replace("Z", "+00:00")
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
