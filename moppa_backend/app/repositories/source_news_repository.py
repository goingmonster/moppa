from datetime import datetime
from collections.abc import Sequence
from typing import TypedDict

from sqlalchemy import create_engine, text
from sqlalchemy.engine import RowMapping

from app.config import settings


class SourceNewsRow(TypedDict):
    source_information: str | None
    create_time: datetime
    source_site: str | None
    published: datetime | None
    url: str | None
    title_translate: str | None
    text_translate: str | None
    type: str | None
    entities: object | None


class SourceNewsRepository:
    def fetch_latest_rows(self, limit: int) -> list[SourceNewsRow]:
        schema = self._safe_identifier(settings.source_db_schema)
        query = text(
            f"""
            SELECT source_information, create_time, source_site, published, url, title_translate, text_translate, "type", entities
            FROM {schema}.data_test
            WHERE create_time IS NOT NULL
            ORDER BY create_time DESC, COALESCE(url, '') DESC
            LIMIT :limit
            """
        )

        engine = create_engine(settings.source_database_url, future=True, pool_pre_ping=True)
        try:
            with engine.connect() as connection:
                rows = connection.execute(query, {"limit": limit}).mappings().all()
            return self._normalize_rows(rows)
        finally:
            engine.dispose()

    def fetch_incremental_rows(
        self,
        since: datetime,
        overlap_minutes: int,
        limit: int,
    ) -> list[SourceNewsRow]:
        schema = self._safe_identifier(settings.source_db_schema)
        query = text(
            f"""
            SELECT source_information, create_time, source_site, published, url, title_translate, text_translate, "type", entities
            FROM {schema}.data_test
            WHERE create_time IS NOT NULL
              AND create_time >= (:since - make_interval(mins => :overlap_minutes))
            ORDER BY create_time ASC, COALESCE(url, '') ASC
            LIMIT :limit
            """
        )

        engine = create_engine(settings.source_database_url, future=True, pool_pre_ping=True)
        try:
            with engine.connect() as connection:
                rows = connection.execute(
                    query,
                    {
                        "since": since,
                        "overlap_minutes": overlap_minutes,
                        "limit": limit,
                    },
                ).mappings().all()
            return self._normalize_rows(rows)
        finally:
            engine.dispose()

    def _normalize_rows(self, rows: Sequence[RowMapping]) -> list[SourceNewsRow]:
        return [
            {
                "source_information": row.get("source_information"),
                "create_time": row["create_time"],
                "source_site": row.get("source_site"),
                "published": row.get("published"),
                "url": row.get("url"),
                "title_translate": row.get("title_translate"),
                "text_translate": row.get("text_translate"),
                "type": row.get("type"),
                "entities": row.get("entities"),
            }
            for row in rows
        ]

    def _safe_identifier(self, value: str) -> str:
        sanitized = "".join(char for char in value if char.isalnum() or char == "_")
        return sanitized or "public"
