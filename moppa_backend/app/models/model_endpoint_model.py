from pydantic import BaseModel, Field


class ModelEndpointCreateModel(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    identifier: str = Field(min_length=1, max_length=100)
    provider: str = Field(pattern="^(openai|anthropic|custom|internal)$")
    endpoint_url: str = Field(min_length=1)
    api_key_ref: str | None = None
    model_name: str = Field(min_length=1, max_length=120)
    model_version: str = Field(default="v1.0", min_length=1, max_length=40)
    max_tokens: int = Field(default=4096, ge=1)
    temperature: float = Field(default=0.7, ge=0, le=2)
    timeout_seconds: int = Field(default=120, ge=1)
    is_available: bool = True
    status: str = Field(default="active", pattern="^(active|inactive|archived)$")


class ModelEndpointUpdateModel(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    identifier: str | None = Field(default=None, min_length=1, max_length=100)
    provider: str | None = Field(default=None, pattern="^(openai|anthropic|custom|internal)$")
    endpoint_url: str | None = Field(default=None, min_length=1)
    api_key_ref: str | None = None
    model_name: str | None = Field(default=None, min_length=1, max_length=120)
    model_version: str | None = Field(default=None, min_length=1, max_length=40)
    max_tokens: int | None = Field(default=None, ge=1)
    temperature: float | None = Field(default=None, ge=0, le=2)
    timeout_seconds: int | None = Field(default=None, ge=1)
    is_available: bool | None = None
    status: str | None = Field(default=None, pattern="^(active|inactive|archived)$")


class ModelEndpointListItemModel(BaseModel):
    id: str
    name: str
    identifier: str
    provider: str
    endpoint_url: str
    api_key_ref: str | None
    model_name: str
    model_version: str
    max_tokens: int
    temperature: float
    timeout_seconds: int
    is_available: bool
    status: str
    created_at: str
    updated_at: str


class ModelEndpointPaginationResponse(BaseModel):
    page: int
    page_size: int
    total: int
    items: list[ModelEndpointListItemModel]
