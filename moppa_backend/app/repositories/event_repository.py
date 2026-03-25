from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import func, or_, select, text, update
from sqlalchemy.orm import Session

from app.db.models import EventEntity
from app.models.event_model import EventCreateModel, EventUpdateModel


class EventRepository:
    def __init__(self, db: Session) -> None:
        self.db: Session = db

    def create(self, payload: EventCreateModel) -> str:
        entity = EventEntity(
            event_key=payload.event_key,
            title=payload.title,
            content=payload.content,
            source_system=payload.source_system,
            credibility_level=payload.credibility_level,
            event_time=payload.event_time,
            url=payload.url,
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
                .order_by(EventEntity.event_time.desc())
                .offset(offset)
                .limit(page_size)
            )
        )
        total = self.db.scalar(
            select(func.count()).select_from(EventEntity).where(EventEntity.deleted_at.is_(None))
        )
        return items, int(total or 0)

    def list_pending_for_auto_review(self, limit: int) -> list[EventEntity]:
        return list(
            self.db.scalars(
                select(EventEntity)
                .where(
                    EventEntity.deleted_at.is_(None),
                    EventEntity.filter_status == "pending",
                )
                .order_by(EventEntity.created_at.asc())
                .limit(limit)
            )
        )

    def list_passed_today(
        self,
        day_start: datetime,
        day_end: datetime,
        limit: int,
        offset: int,
        source_systems: list[str] | None = None,
    ) -> list[EventEntity]:
        query = select(EventEntity).where(
            EventEntity.deleted_at.is_(None),
            EventEntity.filter_status == "passed",
            EventEntity.event_time >= day_start,
            EventEntity.event_time < day_end,
        )
        if source_systems:
            query = query.where(EventEntity.source_system.in_(source_systems))
        return list(
            self.db.scalars(
                query
                .order_by(EventEntity.event_time.asc(), EventEntity.id.asc())
                .offset(offset)
                .limit(limit)
            )
        )

    def list_passed(self, limit: int, offset: int, source_systems: list[str] | None = None) -> list[EventEntity]:
        query = select(EventEntity).where(
            EventEntity.deleted_at.is_(None),
            EventEntity.filter_status == "passed",
        )
        if source_systems:
            query = query.where(EventEntity.source_system.in_(source_systems))
        return list(
            self.db.scalars(
                query
                .order_by(EventEntity.event_time.asc(), EventEntity.id.asc())
                .offset(offset)
                .limit(limit)
            )
        )

    def count_passed(
        self,
        day_start: datetime | None = None,
        day_end: datetime | None = None,
        source_systems: list[str] | None = None,
    ) -> int:
        query = select(func.count()).select_from(EventEntity).where(
            EventEntity.deleted_at.is_(None),
            EventEntity.filter_status == "passed",
        )
        if day_start is not None:
            query = query.where(EventEntity.event_time >= day_start)
        if day_end is not None:
            query = query.where(EventEntity.event_time < day_end)
        if source_systems:
            query = query.where(EventEntity.source_system.in_(source_systems))
        total = self.db.scalar(query)
        return int(total or 0)

    def search_paginated(
        self,
        keyword: str,
        source_system: str,
        filter_status: str,
        event_time_from: datetime | None,
        event_time_to: datetime | None,
        page: int,
        page_size: int,
    ) -> tuple[list[EventEntity], int]:
        offset = (page - 1) * page_size
        base_query = select(EventEntity).where(EventEntity.deleted_at.is_(None))
        count_query = select(func.count()).select_from(EventEntity).where(EventEntity.deleted_at.is_(None))

        normalized = keyword.strip()
        if normalized:
            escaped = normalized.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            pattern = f"%{escaped}%"
            condition = or_(
                EventEntity.title.ilike(pattern, escape="\\"),
                EventEntity.content.ilike(pattern, escape="\\"),
            )
            base_query = base_query.where(condition)
            count_query = count_query.where(condition)

        normalized_source_system = source_system.strip()
        if normalized_source_system:
            base_query = base_query.where(EventEntity.source_system == normalized_source_system)
            count_query = count_query.where(EventEntity.source_system == normalized_source_system)

        status = filter_status.strip()
        if status:
            if status == "reviewed":
                reviewed_statuses = ["passed", "filtered"]
                base_query = base_query.where(EventEntity.filter_status.in_(reviewed_statuses))
                count_query = count_query.where(EventEntity.filter_status.in_(reviewed_statuses))
            else:
                base_query = base_query.where(EventEntity.filter_status == status)
                count_query = count_query.where(EventEntity.filter_status == status)

        if event_time_from is not None:
            base_query = base_query.where(EventEntity.event_time >= event_time_from)
            count_query = count_query.where(EventEntity.event_time >= event_time_from)

        if event_time_to is not None:
            base_query = base_query.where(EventEntity.event_time <= event_time_to)
            count_query = count_query.where(EventEntity.event_time <= event_time_to)

        items = list(
            self.db.scalars(
                base_query
                .order_by(EventEntity.event_time.desc())
                .offset(offset)
                .limit(page_size)
            )
        )
        total = self.db.scalar(count_query)
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
        title: str,
        content: str,
        source_system: str,
        credibility_level: int,
        event_time: datetime,
        url: str | None,
        trace_id: UUID,
        metadata: dict[str, object] | None = None,
        version: str = "v1.0",
    ) -> tuple[EventEntity, bool]:
        existing = self.db.scalar(
            select(EventEntity).where(EventEntity.event_key == event_key, EventEntity.__table__.c.version == version)
        )
        if existing is not None:
            return existing, False

        entity = EventEntity(
            event_key=event_key,
            title=title,
            content=content,
            source_system=source_system,
            credibility_level=credibility_level,
            event_time=event_time,
            url=url,
            metadata_=metadata or {},
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

    def apply_auto_review_result(
        self,
        event_id: UUID,
        status: str,
        tags: list[str],
        reasons: list[str],
    ) -> EventEntity | None:
        entity = self.db.get(EventEntity, event_id)
        if entity is None:
            return None
        _ = self.db.execute(
            text(
                """
                UPDATE event
                SET filter_status = :status,
                    tags = :tags,
                    filter_reasons = :reasons,
                    updated_at = :updated_at
                WHERE id = :event_id
                """
            ),
            {
                "status": status,
                "tags": tags,
                "reasons": reasons,
                "updated_at": datetime.now(timezone.utc),
                "event_id": str(event_id),
            },
        )
        self.db.commit()
        self.db.refresh(entity)
        return entity

    def batch_mark_matched(self, event_ids: list[UUID]) -> int:
        if not event_ids:
            return 0
        now = datetime.now(timezone.utc)
        result = self.db.execute(
            update(EventEntity)
            .where(
                EventEntity.id.in_(event_ids),
                EventEntity.deleted_at.is_(None),
            )
            .values(
                filter_status="matched",
                updated_at=now,
            )
        )
        self.db.commit()
        return int(result.rowcount or 0)

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
        if payload.title is not None:
            entity.title = payload.title
        if payload.source_system is not None:
            entity.source_system = payload.source_system
        if payload.credibility_level is not None:
            entity.credibility_level = payload.credibility_level
        if payload.filter_status is not None:
            entity.filter_status = payload.filter_status
        if payload.url is not None:
            entity.url = payload.url

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
