from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.models.model_endpoint_model import ModelEndpointCreateModel, ModelEndpointUpdateModel


class ModelEndpointRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_paginated(self, page: int, page_size: int) -> tuple[list[dict[str, object]], int]:
        offset = (page - 1) * page_size
        items = self.db.execute(
            text(
                """
                SELECT id, name, identifier, provider, endpoint_url, api_key_ref,
                       model_name, model_version, max_tokens, temperature,
                       timeout_seconds, is_available, status, created_at, updated_at
                FROM model_endpoint
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
                FROM model_endpoint
                WHERE deleted_at IS NULL
                """
            )
        ).scalar_one()
        return [dict(row) for row in items], int(total)

    def create(self, payload: ModelEndpointCreateModel) -> dict[str, object]:
        row = self.db.execute(
            text(
                """
                INSERT INTO model_endpoint (
                    name, identifier, provider, endpoint_url, api_key_ref,
                    model_name, model_version, max_tokens, temperature,
                    timeout_seconds, is_available, status
                )
                VALUES (
                    :name, :identifier, :provider, :endpoint_url, :api_key_ref,
                    :model_name, :model_version, :max_tokens, :temperature,
                    :timeout_seconds, :is_available, :status
                )
                RETURNING id, name, identifier, provider, endpoint_url, api_key_ref,
                          model_name, model_version, max_tokens, temperature,
                          timeout_seconds, is_available, status, created_at, updated_at
                """
            ),
            {
                "name": payload.name,
                "identifier": payload.identifier,
                "provider": payload.provider,
                "endpoint_url": payload.endpoint_url,
                "api_key_ref": payload.api_key_ref,
                "model_name": payload.model_name,
                "model_version": payload.model_version,
                "max_tokens": payload.max_tokens,
                "temperature": payload.temperature,
                "timeout_seconds": payload.timeout_seconds,
                "is_available": payload.is_available,
                "status": payload.status,
            },
        ).mappings().one()
        self.db.commit()
        return dict(row)

    def get_by_id(self, endpoint_id: str) -> dict[str, object] | None:
        row = self.db.execute(
            text(
                """
                SELECT id, name, identifier, provider, endpoint_url, api_key_ref,
                       model_name, model_version, max_tokens, temperature,
                       timeout_seconds, is_available, status, created_at, updated_at
                FROM model_endpoint
                WHERE id = :endpoint_id AND deleted_at IS NULL
                """
            ),
            {"endpoint_id": str(UUID(endpoint_id))},
        ).mappings().first()
        return dict(row) if row else None

    def update(self, endpoint_id: str, payload: ModelEndpointUpdateModel) -> dict[str, object] | None:
        current = self.get_by_id(endpoint_id)
        if current is None:
            return None

        merged = {
            "name": payload.name if payload.name is not None else current["name"],
            "identifier": payload.identifier if payload.identifier is not None else current["identifier"],
            "provider": payload.provider if payload.provider is not None else current["provider"],
            "endpoint_url": payload.endpoint_url if payload.endpoint_url is not None else current["endpoint_url"],
            "api_key_ref": payload.api_key_ref if payload.api_key_ref is not None else current["api_key_ref"],
            "model_name": payload.model_name if payload.model_name is not None else current["model_name"],
            "model_version": payload.model_version if payload.model_version is not None else current["model_version"],
            "max_tokens": payload.max_tokens if payload.max_tokens is not None else current["max_tokens"],
            "temperature": payload.temperature if payload.temperature is not None else current["temperature"],
            "timeout_seconds": payload.timeout_seconds if payload.timeout_seconds is not None else current["timeout_seconds"],
            "is_available": payload.is_available if payload.is_available is not None else current["is_available"],
            "status": payload.status if payload.status is not None else current["status"],
        }

        row = self.db.execute(
            text(
                """
                UPDATE model_endpoint
                SET name = :name,
                    identifier = :identifier,
                    provider = :provider,
                    endpoint_url = :endpoint_url,
                    api_key_ref = :api_key_ref,
                    model_name = :model_name,
                    model_version = :model_version,
                    max_tokens = :max_tokens,
                    temperature = :temperature,
                    timeout_seconds = :timeout_seconds,
                    is_available = :is_available,
                    status = :status,
                    updated_at = :updated_at
                WHERE id = :endpoint_id AND deleted_at IS NULL
                RETURNING id, name, identifier, provider, endpoint_url, api_key_ref,
                          model_name, model_version, max_tokens, temperature,
                          timeout_seconds, is_available, status, created_at, updated_at
                """
            ),
            {**merged, "endpoint_id": str(UUID(endpoint_id)), "updated_at": datetime.now(timezone.utc)},
        ).mappings().first()
        self.db.commit()
        return dict(row) if row else None

    def list_active(self) -> list[dict[str, object]]:
        rows = self.db.execute(
            text(
                """
                SELECT id, name, identifier, provider, endpoint_url, api_key_ref,
                       model_name, model_version, max_tokens, temperature,
                       timeout_seconds, is_available, status
                FROM model_endpoint
                WHERE deleted_at IS NULL
                  AND is_available = TRUE
                  AND status = 'active'
                ORDER BY created_at ASC
                """
            )
        ).mappings().all()
        return [dict(row) for row in rows]

    def batch_soft_delete(self, ids: list[str]) -> int:
        now = datetime.now(timezone.utc)
        uuid_ids = [str(UUID(eid)) for eid in ids]
        result = self.db.execute(
            text(
                """
                UPDATE model_endpoint
                SET deleted_at = :deleted_at,
                    updated_at = :updated_at
                WHERE id = ANY(CAST(:ids AS uuid[]))
                  AND deleted_at IS NULL
                """
            ),
            {"deleted_at": now, "updated_at": now, "ids": uuid_ids},
        )
        self.db.commit()
        return int(getattr(result, "rowcount", 0) or 0)
