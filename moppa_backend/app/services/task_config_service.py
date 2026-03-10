from sqlalchemy.orm import Session

from app.db.models import SystemConfigEntity
from app.models.task_config_model import TaskConfigCreateModel, TaskConfigUpdateModel
from app.repositories.task_config_repository import TaskConfigRepository


class TaskConfigService:
    def __init__(self, db: Session) -> None:
        self.repository = TaskConfigRepository(db)

    def create(self, payload: TaskConfigCreateModel) -> SystemConfigEntity:
        return self.repository.create(
            task_type=payload.task_type,
            value=payload.config.model_dump(),
            description=payload.description,
        )

    def list_paginated(self, page: int, page_size: int) -> tuple[list[SystemConfigEntity], int]:
        return self.repository.list_paginated(page, page_size)

    def get_by_task_type(self, task_type: str) -> SystemConfigEntity | None:
        return self.repository.get_by_task_type(task_type)

    def update(self, task_type: str, payload: TaskConfigUpdateModel) -> SystemConfigEntity | None:
        value = payload.config.model_dump() if payload.config is not None else None
        return self.repository.update(task_type=task_type, value=value, description=payload.description)

    def delete(self, task_type: str) -> bool:
        return self.repository.delete(task_type)
