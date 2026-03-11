from datetime import datetime

from pydantic import BaseModel, Field


class QuestionTemplateCreateModel(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    level: int = Field(ge=1, le=4)
    category: str | None = Field(default=None, max_length=100)
    template_content: str = Field(min_length=1)
    variables: list[object] = Field(default_factory=list)
    generation_config: dict[str, object] = Field(default_factory=dict)
    verification_conditions: dict[str, object] = Field(default_factory=dict)
    duplicate_check_window: str = Field(default="7 days", min_length=1)
    max_duplicate_rate: float = Field(default=5.0, ge=0, le=100)
    status: str = Field(default="active", pattern="^(active|inactive|archived)$")
    version: str = Field(default="v1.0", min_length=1, max_length=20)


class QuestionTemplateUpdateModel(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    level: int | None = Field(default=None, ge=1, le=4)
    category: str | None = Field(default=None, max_length=100)
    template_content: str | None = Field(default=None, min_length=1)
    variables: list[object] | None = None
    generation_config: dict[str, object] | None = None
    verification_conditions: dict[str, object] | None = None
    duplicate_check_window: str | None = Field(default=None, min_length=1)
    max_duplicate_rate: float | None = Field(default=None, ge=0, le=100)
    status: str | None = Field(default=None, pattern="^(active|inactive|archived)$")
    version: str | None = Field(default=None, min_length=1, max_length=20)


class QuestionTemplateListItemModel(BaseModel):
    id: str
    name: str
    level: int
    category: str | None
    template_content: str
    variables: list[object]
    generation_config: dict[str, object]
    verification_conditions: dict[str, object]
    duplicate_check_window: str
    max_duplicate_rate: float
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
