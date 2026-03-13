from pydantic import BaseModel, Field


class QuestionCommentCreateModel(BaseModel):
    question_id: str = Field(min_length=1)
    content: str = Field(min_length=1)


class QuestionCommentUpdateModel(BaseModel):
    content: str = Field(min_length=1)


class QuestionCommentItemModel(BaseModel):
    id: str
    question_id: str
    user_id: str
    username: str
    content: str
    created_at: str
    updated_at: str


class QuestionCommentListResponse(BaseModel):
    items: list[QuestionCommentItemModel]
