from sqlalchemy import text
from sqlalchemy.orm import Session


class DataSourceRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def exists_active_source_system(self, source_system: str) -> bool:
        row = self.db.execute(
            text(
                """
                SELECT 1
                FROM data_source
                WHERE source_system = :source_system
                  AND is_active = TRUE
                  AND deleted_at IS NULL
                LIMIT 1
                """
            ),
            {"source_system": source_system},
        ).fetchone()
        return row is not None
