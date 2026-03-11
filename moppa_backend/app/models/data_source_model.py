from pydantic import BaseModel, Field


class DataSourceCreateModel(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    source_system: str = Field(min_length=1, max_length=100)
    source_type: str = Field(pattern="^(api|database|file|websocket)$")
    connection_config: dict[str, object] = Field(default_factory=dict)
    secret_ref: str | None = None
    credibility_level: int = Field(default=3, ge=1, le=5)
    sync_frequency: str = Field(default="1 hour", min_length=1)
    is_active: bool = True
    version: str = Field(default="v1.0", min_length=1, max_length=20)


class DataSourceListItemModel(BaseModel):
    id: str
    name: str
    source_system: str
    source_type: str
    connection_config: dict[str, object]
    secret_ref: str | None
    credibility_level: int
    sync_frequency: str
    is_active: bool
    version: str
    created_at: str
    updated_at: str


class DataSourcePaginationResponse(BaseModel):
    page: int
    page_size: int
    total: int
    items: list[DataSourceListItemModel]


class DataSourceUpdateModel(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    source_system: str | None = Field(default=None, min_length=1, max_length=100)
    source_type: str | None = Field(default=None, pattern="^(api|database|file|websocket)$")
    connection_config: dict[str, object] | None = None
    secret_ref: str | None = None
    credibility_level: int | None = Field(default=None, ge=1, le=5)
    sync_frequency: str | None = Field(default=None, min_length=1)
    is_active: bool | None = None
    version: str | None = Field(default=None, min_length=1, max_length=20)
