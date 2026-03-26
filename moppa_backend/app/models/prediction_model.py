from pydantic import BaseModel, Field


class PredictionItemModel(BaseModel):
    id: str
    question_id: str
    model_id: str
    model_name: str
    model_identifier: str
    prediction_content: str
    confidence: float | None = None
    inference_time_ms: int | None = None
    token_usage: dict[str, object] = Field(default_factory=dict)
    status: str
    error_message: str | None = None
    submission_time: str
    created_at: str
