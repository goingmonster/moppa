from datetime import datetime

from sqlalchemy.orm import Session

from app.db.models import QuestionEntity
from app.models.question_model import QuestionCreateModel, QuestionUpdateModel
from app.repositories.question_repository import QuestionRepository


class QuestionService:
    def __init__(self, db: Session) -> None:
        self.repository = QuestionRepository(db)

    def create(self, payload: QuestionCreateModel) -> str:
        return self.repository.create(payload)

    def list_paginated(
        self,
        page: int,
        page_size: int,
        *,
        event_domain: str = "",
        event_type: str = "",
        status: str = "",
        level: int | None = None,
        created_from: datetime | None = None,
        created_to: datetime | None = None,
        deleted_mode: str = "active_only",
    ) -> tuple[list[QuestionEntity], int]:
        return self.repository.list_paginated(
            page,
            page_size,
            event_domain=event_domain,
            event_type=event_type,
            status=status,
            level=level,
            created_from=created_from,
            created_to=created_to,
            deleted_mode=deleted_mode,
        )

    def search_paginated(
        self,
        keyword: str,
        page: int,
        page_size: int,
        *,
        event_domain: str = "",
        event_type: str = "",
        status: str = "",
        level: int | None = None,
        created_from: datetime | None = None,
        created_to: datetime | None = None,
        deleted_mode: str = "active_only",
    ) -> tuple[list[QuestionEntity], int]:
        return self.repository.search_paginated(
            keyword,
            page,
            page_size,
            event_domain=event_domain,
            event_type=event_type,
            status=status,
            level=level,
            created_from=created_from,
            created_to=created_to,
            deleted_mode=deleted_mode,
        )

    def get_by_id(self, question_id: str) -> QuestionEntity | None:
        return self.repository.get_by_id(question_id)

    def update(self, question_id: str, payload: QuestionUpdateModel) -> QuestionEntity | None:
        return self.repository.update(question_id, payload)

    def batch_delete(self, ids: list[str], delete_reason: str) -> int:
        return self.repository.batch_soft_delete(ids, delete_reason)

    def get_event_ids_map(self, question_ids: list[str]) -> dict[str, list[str]]:
        return self.repository.get_event_ids_map(question_ids)

    def get_event_ids(self, question_id: str) -> list[str]:
        return self.repository.get_event_ids(question_id)

    def get_coordinates_map(self, question_ids: list[str]) -> dict[str, dict[str, float]]:
        return self.repository.get_coordinates_map(question_ids)
