from uuid import UUID

from pydantic import BaseModel, Field


class ApiKeyCreateModel(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    user_type: str = Field(pattern="^(agent|user|other)$")
    purpose: str | None = Field(default=None, max_length=50)


class ApiKeyUpdateModel(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    user_type: str | None = Field(default=None, pattern="^(agent|user|other)$")
    purpose: str | None = Field(default=None, max_length=50)
    is_active: bool | None = None


class ApiKeyListItemModel(BaseModel):
    id: str
    name: str
    token: str
    user_type: str
    purpose: str | None
    is_active: bool
    last_used_at: str | None
    created_by: str | None
    created_at: str


class ApiKeyPaginationResponse(BaseModel):
    page: int
    page_size: int
    total: int
    items: list[ApiKeyListItemModel]
