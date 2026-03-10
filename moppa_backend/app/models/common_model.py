from pydantic import BaseModel, Field


class BatchDeleteRequest(BaseModel):
    ids: list[str] = Field(min_length=1)


class BatchDeleteResponse(BaseModel):
    deleted_count: int
