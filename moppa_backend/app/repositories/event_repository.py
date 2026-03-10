from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.db.models import EventEntity
from app.models.event_model import EventCreateModel, EventUpdateModel


class EventRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, payload: EventCreateModel) -> str:
        entity = EventEntity(
            event_key=payload.event_key,
            content=payload.content,
            source_system=payload.source_system,
            credibility_level=payload.credibility_level,
            event_time=payload.event_time,
            trace_id=payload.trace_id,
            filter_status="pending",
        )
        self.db.add(entity)
        self.db.flush()
        self.db.commit()
        return str(entity.id)

    def list_paginated(self, page: int, page_size: int) -> tuple[list[EventEntity], int]:
        offset = (page - 1) * page_size
        items = list(
            self.db.scalars(
                select(EventEntity)
                .where(EventEntity.deleted_at.is_(None))
                .order_by(EventEntity.created_at.desc())
                .offset(offset)
                .limit(page_size)
            )
        )
        total = self.db.scalar(
            select(func.count()).select_from(EventEntity).where(EventEntity.deleted_at.is_(None))
        )
        return items, int(total or 0)

    def get_by_event_key(self, event_key: str, version: str = "v1.0") -> EventEntity | None:
        return self.db.scalar(
            select(EventEntity).where(
                EventEntity.event_key == event_key,
                EventEntity.deleted_at.is_(None),
                EventEntity.__table__.c.version == version,
            )
        )

    def ingest_event(
        self,
        event_key: str,
        content: str,
        source_system: str,
        credibility_level: int,
        event_time: datetime,
        trace_id: UUID,
        version: str = "v1.0",
    ) -> tuple[EventEntity, bool]:
        existing = self.db.scalar(
            select(EventEntity).where(EventEntity.event_key == event_key, EventEntity.__table__.c.version == version)
        )
        if existing is not None:
            return existing, False

        entity = EventEntity(
            event_key=event_key,
            content=content,
            source_system=source_system,
            credibility_level=credibility_level,
            event_time=event_time,
            trace_id=trace_id,
            filter_status="pending",
        )
        self.db.add(entity)
        self.db.flush()
        self.db.commit()
        self.db.refresh(entity)
        return entity, True

    def set_filter_result(self, event_id: UUID, status: str, reasons: list[str]) -> EventEntity | None:
        entity = self.db.get(EventEntity, event_id)
        if entity is None:
            return None
        _ = self.db.execute(
            text(
                """
                UPDATE event
                SET filter_status = :status,
                    filter_reasons = :reasons,
                    updated_at = :updated_at
                WHERE id = :event_id
                """
            ),
            {
                "status": status,
                "reasons": reasons,
                "updated_at": datetime.now(timezone.utc),
                "event_id": str(event_id),
            },
        )
        self.db.commit()
        self.db.refresh(entity)
        return entity

    def get_by_id(self, event_id: str) -> EventEntity | None:
        entity = self.db.get(EventEntity, UUID(event_id))
        if entity is None or entity.deleted_at is not None:
            return None
        return entity

    def update(self, event_id: str, payload: EventUpdateModel) -> EventEntity | None:
        entity = self.get_by_id(event_id)
        if entity is None:
            return None

        if payload.content is not None:
            entity.content = payload.content
        if payload.source_system is not None:
            entity.source_system = payload.source_system
        if payload.credibility_level is not None:
            entity.credibility_level = payload.credibility_level
        if payload.filter_status is not None:
            entity.filter_status = payload.filter_status

        self.db.commit()
        self.db.refresh(entity)
        return entity

    def batch_soft_delete(self, ids: list[str]) -> int:
        uuid_ids = [UUID(value) for value in ids]
        entities = list(self.db.scalars(select(EventEntity).where(EventEntity.id.in_(uuid_ids))))
        now = datetime.now(timezone.utc)
        changed = 0
        for entity in entities:
            if entity.deleted_at is None:
                entity.deleted_at = now
                changed += 1
        self.db.commit()
        return changed
