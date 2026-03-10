from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import TaskExecutionEntity
from app.models.task_execution_model import TaskExecutionCreateModel, TaskExecutionUpdateModel


class TaskExecutionRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, payload: TaskExecutionCreateModel) -> str:
        entity = TaskExecutionEntity(
            task_type=payload.task_type,
            idempotency_key=payload.idempotency_key,
            trace_id=payload.trace_id,
            status="pending",
            attempt_count=0,
        )
        self.db.add(entity)
        self.db.flush()
        self.db.commit()
        return str(entity.id)

    def list_paginated(self, page: int, page_size: int) -> tuple[list[TaskExecutionEntity], int]:
        offset = (page - 1) * page_size
        items = list(
            self.db.scalars(
                select(TaskExecutionEntity)
                .order_by(TaskExecutionEntity.created_at.desc())
                .offset(offset)
                .limit(page_size)
            )
        )
        total = self.db.scalar(select(func.count()).select_from(TaskExecutionEntity))
        return items, int(total or 0)

    def get_by_id(self, task_id: str) -> TaskExecutionEntity | None:
        return self.db.get(TaskExecutionEntity, UUID(task_id))

    def update_status(self, task_id: str, status: str) -> bool:
        entity = self.get_by_id(task_id)
        if entity is None:
            return False
        entity.status = status
        self.db.commit()
        return True

    def update(self, task_id: str, payload: TaskExecutionUpdateModel) -> TaskExecutionEntity | None:
        entity = self.get_by_id(task_id)
        if entity is None:
            return None

        if payload.task_type is not None:
            entity.task_type = payload.task_type
        if payload.idempotency_key is not None:
            entity.idempotency_key = payload.idempotency_key
        if payload.status is not None:
            entity.status = payload.status
        if payload.attempt_count is not None:
            entity.attempt_count = payload.attempt_count

        self.db.commit()
        self.db.refresh(entity)
        return entity

    def batch_delete(self, ids: list[str]) -> int:
        uuid_ids = [UUID(value) for value in ids]
        entities = list(self.db.scalars(select(TaskExecutionEntity).where(TaskExecutionEntity.id.in_(uuid_ids))))
        count = len(entities)
        for entity in entities:
            self.db.delete(entity)
        self.db.commit()
        return count
