from datetime import datetime

from pydantic import BaseModel, Field


class EventFilterRuleCreateModel(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    level: int = Field(ge=1, le=4)
    filter_expression: str = Field(min_length=1)
    filter_config: dict[str, object] = Field(default_factory=dict)
    priority: int = 0
    status: str = Field(default="active", pattern="^(active|inactive|archived)$")
    version: str = Field(default="v1.0", min_length=1, max_length=20)


class EventFilterRuleUpdateModel(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    level: int | None = Field(default=None, ge=1, le=4)
    filter_expression: str | None = Field(default=None, min_length=1)
    filter_config: dict[str, object] | None = None
    priority: int | None = None
    status: str | None = Field(default=None, pattern="^(active|inactive|archived)$")
    version: str | None = Field(default=None, min_length=1, max_length=20)


class EventFilterRuleListItemModel(BaseModel):
    id: str
    name: str
    level: int
    filter_expression: str
    filter_config: dict[str, object]
    priority: int
    status: str
    version: str
    created_at: datetime
    updated_at: datetime


class EventFilterRulePaginationResponse(BaseModel):
    page: int
    page_size: int
    total: int
    items: list[EventFilterRuleListItemModel]
