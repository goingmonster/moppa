from __future__ import annotations

from dataclasses import dataclass
import logging
from typing import cast

import requests


@dataclass(frozen=True)
class TavilySearchResult:
    title: str
    url: str
    content: str
    score: float | None
    published_date: str | None
    raw: dict[str, object]


_logger = logging.getLogger(__name__)


class TavilySearchClient:
    def __init__(self, api_keys: list[str], timeout_seconds: int = 30) -> None:
        self.api_keys: list[str] = [item.strip() for item in api_keys if item.strip()]
        self.timeout_seconds: int = timeout_seconds

    def search_news(
        self,
        *,
        query: str,
        max_results: int,
        search_depth: str,
        time_range: str,
    ) -> list[TavilySearchResult]:
        if not self.api_keys:
            raise ValueError("TAVILY_KEYS is required")

        errors: list[str] = []
        normalized_max_results = max(1, min(max_results, 20))

        for key_index, api_key in enumerate(self.api_keys, start=1):
            masked_key = self._mask_key(api_key)
            payload = {
                "api_key": api_key,
                "query": query,
                "topic": "news",
                "search_depth": search_depth,
                "time_range": time_range,
                "max_results": normalized_max_results,
                "include_answer": False,
                "include_raw_content": False,
            }
            _logger.info(
                "Tavily fetch started: query=%s key_index=%s key=%s max_results=%s search_depth=%s time_range=%s",
                query,
                key_index,
                masked_key,
                normalized_max_results,
                search_depth,
                time_range,
            )
            try:
                response = requests.post(
                    "https://api.tavily.com/search",
                    json=payload,
                    timeout=self.timeout_seconds,
                )
            except requests.RequestException as exc:
                _logger.warning(
                    "Tavily fetch request failed: query=%s key_index=%s key=%s error=%s",
                    query,
                    key_index,
                    masked_key,
                    str(exc),
                )
                errors.append(f"{type(exc).__name__}: {exc}")
                continue

            if response.status_code == 400:
                _logger.error(
                    "Tavily fetch rejected: query=%s key_index=%s key=%s status_code=%s body=%s",
                    query,
                    key_index,
                    masked_key,
                    response.status_code,
                    response.text,
                )
                raise ValueError(f"Tavily request rejected: {response.text}")

            if response.status_code >= 400:
                _logger.warning(
                    "Tavily fetch non-success response: query=%s key_index=%s key=%s status_code=%s body=%s",
                    query,
                    key_index,
                    masked_key,
                    response.status_code,
                    response.text,
                )
                errors.append(f"HTTP {response.status_code}: {response.text}")
                continue

            payload_obj = cast(object, response.json())
            if not isinstance(payload_obj, dict):
                return []
            response_data = cast(dict[str, object], payload_obj)

            raw_results = response_data.get("results")
            if not isinstance(raw_results, list):
                return []

            items: list[TavilySearchResult] = []
            typed_results = cast(list[object], raw_results)
            for raw in typed_results:
                if not isinstance(raw, dict):
                    continue
                raw_data = cast(dict[str, object], raw)
                title = str(raw_data.get("title") or "").strip()
                url = str(raw_data.get("url") or "").strip()
                content = str(raw_data.get("content") or "").strip()
                if not title and not url and not content:
                    continue

                score_value = raw_data.get("score")
                score = float(score_value) if isinstance(score_value, (int, float)) else None
                published_raw = raw_data.get("published_date")
                published_date = str(published_raw).strip() if published_raw else None
                items.append(
                    TavilySearchResult(
                        title=title,
                        url=url,
                        content=content,
                        score=score,
                        published_date=published_date,
                        raw=raw_data,
                    )
                )
            sample_titles = [item.title for item in items[:3] if item.title]
            _logger.info(
                "Tavily fetch completed: query=%s key_index=%s key=%s fetched=%s sample_titles=%s",
                query,
                key_index,
                masked_key,
                len(items),
                sample_titles,
            )
            return items

        _logger.error(
            "Tavily fetch exhausted all keys: query=%s attempted_keys=%s errors=%s",
            query,
            len(self.api_keys),
            errors,
        )
        raise RuntimeError("All Tavily keys failed: " + " | ".join(errors))

    def _mask_key(self, api_key: str) -> str:
        if len(api_key) <= 8:
            return "****"
        return f"{api_key[:8]}...{api_key[-4:]}"
