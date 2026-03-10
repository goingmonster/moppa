from sqlalchemy.orm import Session

from app.db.models import QuestionEntity
from app.models.question_model import QuestionCreateModel, QuestionUpdateModel
from app.repositories.question_repository import QuestionRepository


class QuestionService:
    def __init__(self, db: Session) -> None:
        self.repository = QuestionRepository(db)

    def create(self, payload: QuestionCreateModel) -> str:
        return self.repository.create(payload)

    def list_paginated(self, page: int, page_size: int) -> tuple[list[QuestionEntity], int]:
        return self.repository.list_paginated(page, page_size)

    def get_by_id(self, question_id: str) -> QuestionEntity | None:
        return self.repository.get_by_id(question_id)

    def update(self, question_id: str, payload: QuestionUpdateModel) -> QuestionEntity | None:
        return self.repository.update(question_id, payload)

    def batch_delete(self, ids: list[str]) -> int:
        return self.repository.batch_soft_delete(ids)
