from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class QuestionCreateModel(BaseModel):
    event_id: UUID | None = None
    event_ids: list[UUID] | None = None
    level: int = Field(ge=1, le=4)
    content: str = Field(min_length=1)
    answer_space: str | None = None
    deadline: datetime
    trace_id: UUID


class QuestionListItemModel(BaseModel):
    id: str
    event_id: str | None = None
    event_ids: list[str] = Field(default_factory=list)
    level: int
    content: str
    answer_space: str | None = None
    deadline: str
    status: str
    trace_id: str


class QuestionPaginationResponse(BaseModel):
    page: int
    page_size: int
    total: int
    items: list[QuestionListItemModel]


class QuestionUpdateModel(BaseModel):
    level: int | None = Field(default=None, ge=1, le=4)
    content: str | None = Field(default=None, min_length=1)
    answer_space: str | None = None
    deadline: datetime | None = None
    status: str | None = Field(default=None, min_length=1)
    event_ids: list[UUID] | None = None
