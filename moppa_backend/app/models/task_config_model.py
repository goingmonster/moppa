from datetime import datetime

from pydantic import BaseModel, Field


class TaskConfigPayloadModel(BaseModel):
    enabled: bool = True
    main_cron: str = Field(default="0 2 * * *", min_length=1)
    compensate_cron: str = Field(default="0 * * * *", min_length=1)
    max_attempts: int = Field(default=3, ge=1, le=10)
    retry_intervals_minutes: list[int] = Field(default_factory=lambda: [1, 5, 15], min_length=1)
    timeout_seconds: int = Field(default=3600, ge=1)
    source_fetch_limit: int = Field(default=200, ge=1, le=5000)


class TaskConfigCreateModel(BaseModel):
    task_type: str = Field(min_length=1, max_length=100)
    description: str | None = None
    config: TaskConfigPayloadModel


class TaskConfigUpdateModel(BaseModel):
    description: str | None = None
    config: TaskConfigPayloadModel | None = None


class TaskConfigItemModel(BaseModel):
    task_type: str
    key: str
    description: str | None
    config: TaskConfigPayloadModel
    created_at: datetime
    updated_at: datetime


class TaskConfigPaginationResponse(BaseModel):
    page: int
    page_size: int
    total: int
    items: list[TaskConfigItemModel]
