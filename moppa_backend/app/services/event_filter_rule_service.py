from sqlalchemy.orm import Session

from app.db.models import EventFilterRuleEntity
from app.models.event_filter_rule_model import EventFilterRuleCreateModel, EventFilterRuleUpdateModel
from app.repositories.event_filter_rule_repository import EventFilterRuleRepository


class EventFilterRuleService:
    def __init__(self, db: Session) -> None:
        self.repository = EventFilterRuleRepository(db)

    def create(self, payload: EventFilterRuleCreateModel) -> EventFilterRuleEntity:
        return self.repository.create(payload)

    def list_paginated(self, page: int, page_size: int, rule_scope: str | None = None) -> tuple[list[EventFilterRuleEntity], int]:
        return self.repository.list_paginated(page, page_size, rule_scope)

    def list_active_rules(self, rule_scope: str | None = None) -> list[EventFilterRuleEntity]:
        return self.repository.list_active_rules(rule_scope)

    def get_by_id(self, rule_id: str) -> EventFilterRuleEntity | None:
        return self.repository.get_by_id(rule_id)

    def update(self, rule_id: str, payload: EventFilterRuleUpdateModel) -> EventFilterRuleEntity | None:
        return self.repository.update(rule_id, payload)

    def soft_delete(self, rule_id: str) -> bool:
        return self.repository.soft_delete(rule_id)
