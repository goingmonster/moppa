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

    def ensure_source_system(self, source_system: str) -> None:
        if self.exists_active_source_system(source_system):
            return
        _ = self.db.execute(
            text(
                """
                INSERT INTO data_source (
                    name, source_system, source_type, connection_config,
                    secret_ref, credibility_level, sync_frequency, is_active, version
                )
                VALUES (
                    :name, :source_system, 'database', '{}'::jsonb,
                    :secret_ref, 3, INTERVAL '1 hour', TRUE, 'v1.0'
                )
                """
            ),
            {
                "name": f"auto-{source_system}",
                "source_system": source_system,
                "secret_ref": "env/source-db",
            },
        )
        self.db.commit()
