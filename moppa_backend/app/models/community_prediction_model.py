from pydantic import BaseModel, Field


class CommunityPredictionCreateModel(BaseModel):
    question_id: str = Field(min_length=1)
    prediction_content: str = Field(min_length=1)
    confidence: float | None = Field(default=None, ge=0, le=100)
    reasoning: str | None = None


class CommunityPredictionUpdateModel(BaseModel):
    prediction_content: str | None = Field(default=None, min_length=1)
    confidence: float | None = Field(default=None, ge=0, le=100)
    reasoning: str | None = None


class CommunityPredictionItemModel(BaseModel):
    id: str
    question_id: str
    user_id: str
    username: str
    prediction_content: str
    confidence: float | None = None
    reasoning: str | None = None
    created_at: str
    updated_at: str


class CommunityPredictionListResponse(BaseModel):
    items: list[CommunityPredictionItemModel]
