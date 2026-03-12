from datetime import datetime

from pydantic import BaseModel, Field


class QuestionTemplateCreateModel(BaseModel):
    question_template: str = Field(min_length=1)
    major_topic: str = Field(min_length=1, max_length=100)
    minor_topic: str = Field(min_length=1, max_length=100)
    difficulty_level: str = Field(pattern="^(L1|L2|L3|L4)$")
    construction_rationale: str = Field(min_length=1)
    candidate_answers: str = Field(min_length=1)
    answer_deadline: datetime
    status: str = Field(default="active", pattern="^(active|inactive|archived)$")
    version: str = Field(default="v1.0", min_length=1, max_length=20)


class QuestionTemplateUpdateModel(BaseModel):
    question_template: str | None = Field(default=None, min_length=1)
    major_topic: str | None = Field(default=None, min_length=1, max_length=100)
    minor_topic: str | None = Field(default=None, min_length=1, max_length=100)
    difficulty_level: str | None = Field(default=None, pattern="^(L1|L2|L3|L4)$")
    construction_rationale: str | None = Field(default=None, min_length=1)
    candidate_answers: str | None = Field(default=None, min_length=1)
    answer_deadline: datetime | None = None
    status: str | None = Field(default=None, pattern="^(active|inactive|archived)$")
    version: str | None = Field(default=None, min_length=1, max_length=20)


class QuestionTemplateListItemModel(BaseModel):
    id: str
    question_template: str
    major_topic: str
    minor_topic: str
    difficulty_level: str
    construction_rationale: str
    candidate_answers: str
    answer_deadline: datetime
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
