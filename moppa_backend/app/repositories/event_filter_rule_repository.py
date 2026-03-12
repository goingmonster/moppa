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
            rule_scope=payload.rule_scope,
            filter_expression=payload.filter_expression,
            filter_prompts=payload.filter_prompts,
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

    def list_paginated(self, page: int, page_size: int, rule_scope: str | None = None) -> tuple[list[EventFilterRuleEntity], int]:
        offset = (page - 1) * page_size
        query = (
            select(EventFilterRuleEntity)
            .where(EventFilterRuleEntity.deleted_at == None)
            .order_by(EventFilterRuleEntity.priority.desc(), EventFilterRuleEntity.created_at.desc())
        )
        count_query = select(func.count()).select_from(EventFilterRuleEntity).where(EventFilterRuleEntity.deleted_at == None)
        if rule_scope is not None:
            query = query.where(EventFilterRuleEntity.rule_scope == rule_scope)
            count_query = count_query.where(EventFilterRuleEntity.rule_scope == rule_scope)

        items = list(
            self.db.scalars(
                query
                .offset(offset)
                .limit(page_size)
            )
        )
        total = self.db.scalar(count_query)
        return items, int(total or 0)

    def list_active_rules(self, rule_scope: str | None = None) -> list[EventFilterRuleEntity]:
        query = (
            select(EventFilterRuleEntity)
            .where(
                EventFilterRuleEntity.deleted_at == None,
                EventFilterRuleEntity.status == "active",
            )
            .order_by(EventFilterRuleEntity.priority.desc(), EventFilterRuleEntity.created_at.asc())
        )
        if rule_scope is not None:
            query = query.where(EventFilterRuleEntity.rule_scope == rule_scope)

        return list(
            self.db.scalars(query)
        )

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
        if payload.rule_scope is not None:
            entity.rule_scope = payload.rule_scope
        if payload.filter_expression is not None:
            entity.filter_expression = payload.filter_expression
        if payload.filter_prompts is not None:
            entity.filter_prompts = payload.filter_prompts
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
