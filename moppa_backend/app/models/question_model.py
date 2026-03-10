from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class QuestionCreateModel(BaseModel):
    event_id: UUID
    level: int = Field(ge=1, le=4)
    content: str = Field(min_length=1)
    deadline: datetime
    trace_id: UUID


class QuestionListItemModel(BaseModel):
    id: str
    event_id: str
    level: int
    content: str
    deadline: str
    status: str
    trace_id: str


class QuestionPaginationResponse(BaseModel):
    page: int
    page_size: int
    total: int
    items: list[QuestionListItemModel]


class QuestionUpdateModel(BaseModel):
    content: str | None = Field(default=None, min_length=1)
    deadline: datetime | None = None
    status: str | None = Field(default=None, min_length=1)
