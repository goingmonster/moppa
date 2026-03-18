from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class QuestionCreateModel(BaseModel):
    event_id: UUID | None = None
    event_ids: list[UUID] | None = None
    template_id: UUID | None = None
    level: int = Field(ge=1, le=4)
    content: str = Field(min_length=1)
    match_score: float | None = None
    event_domain: str | None = None
    event_type: str | None = None
    area: str | None = None
    input_type: str | None = None
    background: str | None = None
    answer_space: str | None = None
    verification_conditions: str | None = None
    deadline: datetime
    status: str | None = None
    trace_id: UUID


class QuestionListItemModel(BaseModel):
    id: str
    event_id: str | None = None
    event_ids: list[str] = Field(default_factory=list)
    template_id: str | None = None
    level: int
    content: str
    match_score: float | None = None
    event_domain: str | None = None
    event_type: str | None = None
    area: str | None = None
    input_type: str | None = None
    background: str | None = None
    answer_space: str | None = None
    verification_conditions: str | None = None
    deadline: str
    status: str
    trace_id: str
    delete_reason: str | None = None
    deleted_at: str | None = None


class QuestionPaginationResponse(BaseModel):
    page: int
    page_size: int
    total: int
    items: list[QuestionListItemModel]


class QuestionUpdateModel(BaseModel):
    level: int | None = Field(default=None, ge=1, le=4)
    content: str | None = Field(default=None, min_length=1)
    match_score: float | None = None
    event_domain: str | None = None
    event_type: str | None = None
    area: str | None = None
    input_type: str | None = None
    background: str | None = None
    answer_space: str | None = None
    deadline: datetime | None = None
    status: str | None = Field(default=None, min_length=1)
    event_ids: list[UUID] | None = None


class QuestionBatchDeleteRequest(BaseModel):
    ids: list[str] = Field(min_length=1)
    delete_reason: str = Field(min_length=1)


class QuestionCommunityStatsItemModel(BaseModel):
    question_id: str
    prediction_count: int
    comment_count: int
    has_prediction: bool
    my_comment_count: int


class QuestionCommunityStatsResponse(BaseModel):
    items: list[QuestionCommunityStatsItemModel]
