from sqlalchemy.orm import Session

from app.db.models import QuestionTemplateEntity
from app.models.question_template_model import QuestionTemplateCreateModel, QuestionTemplateUpdateModel
from app.repositories.question_template_repository import QuestionTemplateRepository


class QuestionTemplateService:
    def __init__(self, db: Session) -> None:
        self.repository = QuestionTemplateRepository(db)

    def create(self, payload: QuestionTemplateCreateModel) -> QuestionTemplateEntity:
        return self.repository.create(payload)

    def get_by_id(self, template_id: str) -> QuestionTemplateEntity | None:
        return self.repository.get_by_id(template_id)

    def list_paginated(self, page: int, page_size: int) -> tuple[list[QuestionTemplateEntity], int]:
        return self.repository.list_paginated(page, page_size)

    def search_paginated(self, keyword: str, page: int, page_size: int) -> tuple[list[QuestionTemplateEntity], int]:
        return self.repository.search_paginated(keyword, page, page_size)

    def list_all(self, keyword: str | None = None) -> list[QuestionTemplateEntity]:
        return self.repository.list_all(keyword)

    def update(self, template_id: str, payload: QuestionTemplateUpdateModel) -> QuestionTemplateEntity | None:
        return self.repository.update(template_id, payload)

    def batch_delete(self, ids: list[str]) -> int:
        return self.repository.batch_soft_delete(ids)
