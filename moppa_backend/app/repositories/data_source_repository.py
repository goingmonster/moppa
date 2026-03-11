import json
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.models.data_source_model import DataSourceCreateModel, DataSourceUpdateModel


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

    def list_paginated(self, page: int, page_size: int) -> tuple[list[dict[str, object]], int]:
        offset = (page - 1) * page_size
        items = self.db.execute(
            text(
                """
                SELECT id, name, source_system, source_type,
                       connection_config, secret_ref, credibility_level,
                       sync_frequency, is_active, version, created_at, updated_at
                FROM data_source
                WHERE deleted_at IS NULL
                ORDER BY created_at DESC
                OFFSET :offset LIMIT :limit
                """
            ),
            {"offset": offset, "limit": page_size},
        ).mappings().all()
        total = self.db.execute(
            text(
                """
                SELECT COUNT(*) AS total
                FROM data_source
                WHERE deleted_at IS NULL
                """
            )
        ).scalar_one()
        return [dict(row) for row in items], int(total)

    def create(self, payload: DataSourceCreateModel) -> dict[str, object]:
        row = self.db.execute(
            text(
                """
                INSERT INTO data_source (
                    name, source_system, source_type, connection_config,
                    secret_ref, credibility_level, sync_frequency, is_active, version
                )
                VALUES (
                    :name, :source_system, :source_type, CAST(:connection_config AS jsonb),
                    :secret_ref, :credibility_level, CAST(:sync_frequency AS interval), :is_active, :version
                )
                RETURNING id, name, source_system, source_type,
                          connection_config, secret_ref, credibility_level,
                          sync_frequency, is_active, version, created_at, updated_at
                """
            ),
            {
                "name": payload.name,
                "source_system": payload.source_system,
                "source_type": payload.source_type,
                "connection_config": json.dumps(payload.connection_config),
                "secret_ref": payload.secret_ref,
                "credibility_level": payload.credibility_level,
                "sync_frequency": payload.sync_frequency,
                "is_active": payload.is_active,
                "version": payload.version,
            },
        ).mappings().one()
        self.db.commit()
        return dict(row)

    def get_by_id(self, source_id: str) -> dict[str, object] | None:
        row = self.db.execute(
            text(
                """
                SELECT id, name, source_system, source_type,
                       connection_config, secret_ref, credibility_level,
                       sync_frequency, is_active, version, created_at, updated_at
                FROM data_source
                WHERE id = :source_id AND deleted_at IS NULL
                """
            ),
            {"source_id": str(UUID(source_id))},
        ).mappings().first()
        return dict(row) if row else None

    def update(self, source_id: str, payload: DataSourceUpdateModel) -> dict[str, object] | None:
        current = self.get_by_id(source_id)
        if current is None:
            return None

        merged = {
            "name": payload.name if payload.name is not None else current["name"],
            "source_system": payload.source_system if payload.source_system is not None else current["source_system"],
            "source_type": payload.source_type if payload.source_type is not None else current["source_type"],
            "connection_config": (
                payload.connection_config if payload.connection_config is not None else current["connection_config"]
            ),
            "secret_ref": payload.secret_ref if payload.secret_ref is not None else current["secret_ref"],
            "credibility_level": (
                payload.credibility_level if payload.credibility_level is not None else current["credibility_level"]
            ),
            "sync_frequency": payload.sync_frequency if payload.sync_frequency is not None else str(current["sync_frequency"]),
            "is_active": payload.is_active if payload.is_active is not None else current["is_active"],
            "version": payload.version if payload.version is not None else current["version"],
        }

        row = self.db.execute(
            text(
                """
                UPDATE data_source
                SET name = :name,
                    source_system = :source_system,
                    source_type = :source_type,
                    connection_config = CAST(:connection_config AS jsonb),
                    secret_ref = :secret_ref,
                    credibility_level = :credibility_level,
                    sync_frequency = CAST(:sync_frequency AS interval),
                    is_active = :is_active,
                    version = :version,
                    updated_at = :updated_at
                WHERE id = :source_id AND deleted_at IS NULL
                RETURNING id, name, source_system, source_type,
                          connection_config, secret_ref, credibility_level,
                          sync_frequency, is_active, version, created_at, updated_at
                """
            ),
            {
                **merged,
                "source_id": str(UUID(source_id)),
                "updated_at": datetime.now(timezone.utc),
                "connection_config": json.dumps(merged["connection_config"]),
            },
        ).mappings().first()
        self.db.commit()
        return dict(row) if row else None

    def batch_soft_delete(self, ids: list[str]) -> int:
        now = datetime.now(timezone.utc)
        uuid_ids = [str(UUID(source_id)) for source_id in ids]
        result = self.db.execute(
            text(
                """
                UPDATE data_source
                SET deleted_at = :deleted_at,
                    updated_at = :updated_at
                WHERE id = ANY(CAST(:ids AS uuid[]))
                  AND deleted_at IS NULL
                """
            ),
            {"deleted_at": now, "updated_at": now, "ids": uuid_ids},
        )
        self.db.commit()
        rowcount = getattr(result, "rowcount", 0)
        return int(rowcount or 0)
