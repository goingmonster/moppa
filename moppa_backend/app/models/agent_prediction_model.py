from pydantic import BaseModel, Field


class EvidenceItem(BaseModel):
    url: str
    content: str


class AgentPredictionSubmitModel(BaseModel):
    id: str = Field(min_length=1)
    question: str = Field(min_length=1)
    model_name: str = Field(min_length=1, max_length=120)
    answer: str = Field(min_length=1)
    reason: str | None = None
    confidence: int = Field(ge=0, le=100, default=0)
    evidence: list[EvidenceItem] = Field(default_factory=list)


class AgentPredictionItemModel(BaseModel):
    id: str
    question_id: str
    api_key_id: str
    agent_name: str
    user_type: str
    purpose: str | None
    model_name: str
    prediction_content: str
    reasoning: str | None
    confidence: int | None
    evidence: list[EvidenceItem]
    question_text: str
    is_correct: bool | None = None
    score: float | None = None
    status: str
    created_at: str
