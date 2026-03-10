from sqlalchemy.orm import Session

from app.db.models import EventEntity
from app.models.event_model import EventCreateModel, EventUpdateModel
from app.repositories.event_repository import EventRepository


class EventService:
    def __init__(self, db: Session) -> None:
        self.repository = EventRepository(db)

    def create(self, payload: EventCreateModel) -> str:
        return self.repository.create(payload)

    def list_paginated(self, page: int, page_size: int) -> tuple[list[EventEntity], int]:
        return self.repository.list_paginated(page, page_size)

    def get_by_id(self, event_id: str) -> EventEntity | None:
        return self.repository.get_by_id(event_id)

    def update(self, event_id: str, payload: EventUpdateModel) -> EventEntity | None:
        return self.repository.update(event_id, payload)

    def batch_delete(self, ids: list[str]) -> int:
        return self.repository.batch_soft_delete(ids)
