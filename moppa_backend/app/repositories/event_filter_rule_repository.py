from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import EventFilterRuleEntity
from app.models.event_filter_rule_model import EventFilterRuleCreateModel, EventFilterRuleUpdateModel


class EventFilterRuleRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, payload: EventFilterRuleCreateModel) -> EventFilterRuleEntity:
        entity = EventFilterRuleEntity(
            name=payload.name,
            level=payload.level,
            filter_expression=payload.filter_expression,
            filter_config=payload.filter_config,
            priority=payload.priority,
            status=payload.status,
            version=payload.version,
        )
        self.db.add(entity)
        self.db.flush()
        self.db.commit()
        self.db.refresh(entity)
        return entity

    def list_paginated(self, page: int, page_size: int) -> tuple[list[EventFilterRuleEntity], int]:
        offset = (page - 1) * page_size
        items = list(
            self.db.scalars(
                select(EventFilterRuleEntity)
                .where(EventFilterRuleEntity.deleted_at.is_(None))
                .order_by(EventFilterRuleEntity.priority.desc(), EventFilterRuleEntity.created_at.desc())
                .offset(offset)
                .limit(page_size)
            )
        )
        total = self.db.scalar(
            select(func.count()).select_from(EventFilterRuleEntity).where(EventFilterRuleEntity.deleted_at.is_(None))
        )
        return items, int(total or 0)

    def get_by_id(self, rule_id: str) -> EventFilterRuleEntity | None:
        entity = self.db.get(EventFilterRuleEntity, UUID(rule_id))
        if entity is None or entity.deleted_at is not None:
            return None
        return entity

    def update(self, rule_id: str, payload: EventFilterRuleUpdateModel) -> EventFilterRuleEntity | None:
        entity = self.get_by_id(rule_id)
        if entity is None:
            return None

        if payload.name is not None:
            entity.name = payload.name
        if payload.level is not None:
            entity.level = payload.level
        if payload.filter_expression is not None:
            entity.filter_expression = payload.filter_expression
        if payload.filter_config is not None:
            entity.filter_config = payload.filter_config
        if payload.priority is not None:
            entity.priority = payload.priority
        if payload.status is not None:
            entity.status = payload.status
        if payload.version is not None:
            entity.version = payload.version
        entity.updated_at = datetime.now(timezone.utc)

        self.db.commit()
        self.db.refresh(entity)
        return entity

    def soft_delete(self, rule_id: str) -> bool:
        entity = self.get_by_id(rule_id)
        if entity is None:
            return False
        now = datetime.now(timezone.utc)
        entity.deleted_at = now
        entity.updated_at = now
        self.db.commit()
        return True
