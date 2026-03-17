from datetime import datetime

from pydantic import BaseModel, Field


class QuestionTemplateCreateModel(BaseModel):
    template_index: int = Field(ge=1)
    question_template: str = Field(min_length=1)
    difficulty_level: str = Field(pattern="^(L1|L2|L3|L4)$")
    candidate_answer_type: str = Field(pattern="^(fixed|dynamic|open)$")
    event_domain: str = Field(min_length=1, max_length=100)
    event_type: str = Field(min_length=1, max_length=100)
    event_type_id: str = Field(min_length=1, max_length=20)
    operation_level: str = Field(min_length=1, max_length=50)
    status: str = Field(default="active", pattern="^(active|inactive|archived)$")
    version: str = Field(default="v1.0", min_length=1, max_length=20)


class QuestionTemplateUpdateModel(BaseModel):
    template_index: int | None = Field(default=None, ge=1)
    question_template: str | None = Field(default=None, min_length=1)
    difficulty_level: str | None = Field(default=None, pattern="^(L1|L2|L3|L4)$")
    candidate_answer_type: str | None = Field(default=None, pattern="^(fixed|dynamic|open)$")
    event_domain: str | None = Field(default=None, min_length=1, max_length=100)
    event_type: str | None = Field(default=None, min_length=1, max_length=100)
    event_type_id: str | None = Field(default=None, min_length=1, max_length=20)
    operation_level: str | None = Field(default=None, min_length=1, max_length=50)
    status: str | None = Field(default=None, pattern="^(active|inactive|archived)$")
    version: str | None = Field(default=None, min_length=1, max_length=20)


class QuestionTemplateListItemModel(BaseModel):
    id: str
    template_index: int
    question_template: str
    difficulty_level: str
    candidate_answer_type: str
    event_domain: str
    event_type: str
    event_type_id: str
    operation_level: str
    status: str
    version: str
    usage_count: int
    created_at: datetime
    updated_at: datetime


class QuestionTemplatePaginationResponse(BaseModel):
    page: int
    page_size: int
    total: int
    items: list[QuestionTemplateListItemModel]
