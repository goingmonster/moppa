from datetime import datetime
from typing import TypedDict

from sqlalchemy import create_engine, text

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
    def fetch_data_test_rows(self, since: datetime | None, limit: int) -> list[SourceNewsRow]:
        query = text(
            """
            SELECT source_information, create_time, source_site, published, url, title_translate, text_translate, "type", entities
            FROM public.data_test
            WHERE (:since IS NULL OR create_time > :since)
            ORDER BY create_time ASC
            LIMIT :limit
            """
        )

        engine = create_engine(settings.source_database_url, future=True, pool_pre_ping=True)
        try:
            with engine.connect() as connection:
                rows = connection.execute(query, {"since": since, "limit": limit}).mappings().all()
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
        finally:
            engine.dispose()
