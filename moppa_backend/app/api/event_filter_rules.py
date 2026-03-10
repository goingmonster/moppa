from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core import ApiError
from app.db.models import EventFilterRuleEntity
from app.db.session import get_db
from app.models.event_filter_rule_model import (
    EventFilterRuleCreateModel,
    EventFilterRuleListItemModel,
    EventFilterRulePaginationResponse,
    EventFilterRuleUpdateModel,
)
from app.services.event_filter_rule_service import EventFilterRuleService


router = APIRouter(prefix="/event-filter-rules", tags=["event-filter-rules"])


def to_item(entity: EventFilterRuleEntity) -> EventFilterRuleListItemModel:
    return EventFilterRuleListItemModel(
        id=str(entity.id),
        name=entity.name,
        level=entity.level,
        filter_expression=entity.filter_expression,
        filter_config=entity.filter_config,
        priority=entity.priority,
        status=entity.status,
        version=entity.version,
        created_at=entity.created_at,
        updated_at=entity.updated_at,
    )


@router.post("", summary="Create event filter rule")
def create_rule(payload: EventFilterRuleCreateModel, db: Session = Depends(get_db)) -> EventFilterRuleListItemModel:
    service = EventFilterRuleService(db)
    return to_item(service.create(payload))


@router.get("", summary="List event filter rules")
def list_rules(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> EventFilterRulePaginationResponse:
    service = EventFilterRuleService(db)
    rows, total = service.list_paginated(page=page, page_size=page_size)
    return EventFilterRulePaginationResponse(
        page=page,
        page_size=page_size,
        total=total,
        items=[to_item(row) for row in rows],
    )


@router.get("/{rule_id}", summary="Get event filter rule detail")
def get_rule(rule_id: str, db: Session = Depends(get_db)) -> EventFilterRuleListItemModel:
    service = EventFilterRuleService(db)
    entity = service.get_by_id(rule_id)
    if entity is None:
        raise ApiError(status_code=404, code="RULE_NOT_FOUND", message="Event filter rule not found")
    return to_item(entity)


@router.patch("/{rule_id}", summary="Update event filter rule")
def update_rule(
    rule_id: str,
    payload: EventFilterRuleUpdateModel,
    db: Session = Depends(get_db),
) -> EventFilterRuleListItemModel:
    if not payload.model_dump(exclude_none=True):
        raise ApiError(status_code=400, code="EMPTY_UPDATE_PAYLOAD", message="No fields to update")
    service = EventFilterRuleService(db)
    entity = service.update(rule_id, payload)
    if entity is None:
        raise ApiError(status_code=404, code="RULE_NOT_FOUND", message="Event filter rule not found")
    return to_item(entity)


@router.delete("/{rule_id}", summary="Soft delete event filter rule")
def delete_rule(rule_id: str, db: Session = Depends(get_db)) -> dict[str, bool]:
    service = EventFilterRuleService(db)
    deleted = service.soft_delete(rule_id)
    if not deleted:
        raise ApiError(status_code=404, code="RULE_NOT_FOUND", message="Event filter rule not found")
    return {"deleted": True}
