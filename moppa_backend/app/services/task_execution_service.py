from sqlalchemy.orm import Session

from app.db.models import TaskExecutionEntity
from app.models.task_execution_model import TaskExecutionCreateModel, TaskExecutionUpdateModel
from app.repositories.task_execution_repository import TaskExecutionRepository


class TaskExecutionService:
    def __init__(self, db: Session) -> None:
        self.repository = TaskExecutionRepository(db)

    def create(self, payload: TaskExecutionCreateModel) -> str:
        return self.repository.create(payload)

    def list_paginated(self, page: int, page_size: int) -> tuple[list[TaskExecutionEntity], int]:
        return self.repository.list_paginated(page, page_size)

    def get_by_id(self, task_id: str) -> TaskExecutionEntity | None:
        return self.repository.get_by_id(task_id)

    def update(self, task_id: str, payload: TaskExecutionUpdateModel) -> TaskExecutionEntity | None:
        return self.repository.update(task_id, payload)

    def update_status(self, task_id: str, status: str) -> bool:
        return self.repository.update_status(task_id, status)

    def batch_delete(self, ids: list[str]) -> int:
        return self.repository.batch_delete(ids)
