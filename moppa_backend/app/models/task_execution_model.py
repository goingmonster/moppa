from uuid import UUID

from pydantic import BaseModel, Field


class TaskExecutionCreateModel(BaseModel):
    task_type: str = Field(min_length=1)
    idempotency_key: str = Field(min_length=1)
    trace_id: UUID


class TaskExecutionStatusUpdateModel(BaseModel):
    status: str = Field(pattern="^(pending|running|completed|failed|cancelled|dead_letter)$")


class TaskExecutionListItemModel(BaseModel):
    id: str
    task_type: str
    idempotency_key: str
    status: str
    attempt_count: int
    trace_id: str


class TaskExecutionPaginationResponse(BaseModel):
    page: int
    page_size: int
    total: int
    items: list[TaskExecutionListItemModel]


class TaskExecutionUpdateModel(BaseModel):
    task_type: str | None = Field(default=None, min_length=1)
    idempotency_key: str | None = Field(default=None, min_length=1)
    status: str | None = Field(default=None, pattern="^(pending|running|completed|failed|cancelled|dead_letter)$")
    attempt_count: int | None = Field(default=None, ge=0)
