from datetime import datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class S1EventInputModel(BaseModel):
    event_key: str = Field(min_length=1)
    content: str = Field(min_length=1)
    source_system: str = Field(min_length=1)
    credibility_level: int = Field(ge=1, le=5)
    event_time: datetime
    trace_id: UUID = Field(default_factory=uuid4)


class S1PushRequestModel(BaseModel):
    events: list[S1EventInputModel] = Field(min_length=1)


class S1PullNowRequestModel(BaseModel):
    source_system: str | None = None


class S1TaskResponseModel(BaseModel):
    task_id: str
    status: str
    result: dict[str, object]
