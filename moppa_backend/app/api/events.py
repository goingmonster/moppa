from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core import ApiError
from app.db.models import EventEntity
from app.db.session import get_db
from app.models.common_model import BatchDeleteRequest, BatchDeleteResponse
from app.models.event_model import EventCreateModel, EventListItemModel, EventPaginationResponse, EventUpdateModel
from app.services.event_service import EventService

router = APIRouter(prefix="/events", tags=["events"])


def to_event_list_item(entity: EventEntity) -> EventListItemModel:
    return EventListItemModel(
        id=str(entity.id),
        event_key=entity.event_key,
        title=entity.title,
        content=entity.content,
        source_system=entity.source_system,
        credibility_level=entity.credibility_level,
        event_time=entity.event_time.isoformat(),
        filter_status=entity.filter_status,
        trace_id=str(entity.trace_id),
    )


@router.post("", summary="Create event")
def create_event(payload: EventCreateModel, db: Session = Depends(get_db)) -> dict[str, str]:
    service = EventService(db)
    event_id = service.create(payload)
    return {"id": event_id}


@router.get("", summary="List events")
def list_events(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> EventPaginationResponse:
    service = EventService(db)
    rows, total = service.list_paginated(page=page, page_size=page_size)
    items = [to_event_list_item(row) for row in rows]
    return EventPaginationResponse(page=page, page_size=page_size, total=total, items=items)


@router.get("/search", summary="Search events by title/content")
def search_events(
    keyword: str = Query(default=""),
    filter_status: str = Query(default=""),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> EventPaginationResponse:
    service = EventService(db)
    rows, total = service.search_paginated(
        keyword=keyword,
        filter_status=filter_status,
        page=page,
        page_size=page_size,
    )
    items = [to_event_list_item(row) for row in rows]
    return EventPaginationResponse(page=page, page_size=page_size, total=total, items=items)


@router.delete("", summary="Batch delete events")
def delete_events(payload: BatchDeleteRequest, db: Session = Depends(get_db)) -> BatchDeleteResponse:
    service = EventService(db)
    deleted_count = service.batch_delete(payload.ids)
    return BatchDeleteResponse(deleted_count=deleted_count)


@router.get("/{event_id}", summary="Get event detail")
def get_event(event_id: str, db: Session = Depends(get_db)) -> EventListItemModel:
    service = EventService(db)
    entity = service.get_by_id(event_id)
    if entity is None:
        raise ApiError(status_code=404, code="EVENT_NOT_FOUND", message="Event not found")
    return to_event_list_item(entity)


@router.patch("/{event_id}", summary="Update event")
def update_event(event_id: str, payload: EventUpdateModel, db: Session = Depends(get_db)) -> EventListItemModel:
    service = EventService(db)
    if not payload.model_dump(exclude_none=True):
        raise ApiError(status_code=400, code="EMPTY_UPDATE_PAYLOAD", message="No fields to update")
    entity = service.update(event_id, payload)
    if entity is None:
        raise ApiError(status_code=404, code="EVENT_NOT_FOUND", message="Event not found")
    return to_event_list_item(entity)
