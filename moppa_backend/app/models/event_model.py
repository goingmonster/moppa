from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class EventCreateModel(BaseModel):
    event_key: str = Field(min_length=1)
    title: str = Field(min_length=1, max_length=255)
    content: str = Field(min_length=1)
    source_system: str = Field(min_length=1)
    credibility_level: int = Field(ge=1, le=5)
    event_time: datetime
    trace_id: UUID


class EventListItemModel(BaseModel):
    id: str
    event_key: str
    title: str
    content: str
    source_system: str
    credibility_level: int
    event_time: str
    filter_status: str
    trace_id: str


class EventPaginationResponse(BaseModel):
    page: int
    page_size: int
    total: int
    items: list[EventListItemModel]


class EventUpdateModel(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    content: str | None = Field(default=None, min_length=1)
    source_system: str | None = Field(default=None, min_length=1)
    credibility_level: int | None = Field(default=None, ge=1, le=5)
    filter_status: str | None = Field(default=None, min_length=1)
