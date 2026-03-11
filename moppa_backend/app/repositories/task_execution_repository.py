from datetime import datetime, timedelta, timezone
from collections.abc import Mapping
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

    def get_by_idempotency_key(self, idempotency_key: str) -> TaskExecutionEntity | None:
        return self.db.scalar(
            select(TaskExecutionEntity).where(TaskExecutionEntity.idempotency_key == idempotency_key)
        )

    def create_pending(
        self,
        task_type: str,
        idempotency_key: str,
        trace_id: UUID,
        business_id: UUID | None,
        date_window: datetime | None,
    ) -> TaskExecutionEntity:
        entity = TaskExecutionEntity(
            task_type=task_type,
            idempotency_key=idempotency_key,
            trace_id=trace_id,
            status="pending",
            attempt_count=0,
            business_id=business_id,
            date_window=date_window,
        )
        self.db.add(entity)
        self.db.flush()
        self.db.commit()
        self.db.refresh(entity)
        return entity

    def mark_running(self, task_id: UUID) -> TaskExecutionEntity | None:
        entity = self.db.get(TaskExecutionEntity, task_id)
        if entity is None:
            return None
        entity.status = "running"
        entity.started_at = datetime.now(timezone.utc)
        entity.finished_at = None
        entity.error_message = None
        entity.next_retry_at = None
        self.db.commit()
        self.db.refresh(entity)
        return entity

    def mark_completed(
        self,
        task_id: UUID,
        result: Mapping[str, object],
        metrics: Mapping[str, object],
    ) -> TaskExecutionEntity | None:
        entity = self.db.get(TaskExecutionEntity, task_id)
        if entity is None:
            return None
        entity.status = "completed"
        entity.result = dict(result)
        entity.metrics = dict(metrics)
        entity.finished_at = datetime.now(timezone.utc)
        entity.error_message = None
        entity.next_retry_at = None
        self.db.commit()
        self.db.refresh(entity)
        return entity

    def mark_failed(self, task_id: UUID, error_message: str, max_attempts: int = 3) -> TaskExecutionEntity | None:
        entity = self.db.get(TaskExecutionEntity, task_id)
        if entity is None:
            return None
        entity.attempt_count += 1
        entity.error_message = error_message
        entity.finished_at = datetime.now(timezone.utc)
        if entity.attempt_count >= max_attempts:
            entity.status = "dead_letter"
            entity.next_retry_at = None
        else:
            entity.status = "failed"
            backoff_minutes = [1, 5, 15]
            delay = backoff_minutes[min(entity.attempt_count - 1, len(backoff_minutes) - 1)]
            entity.next_retry_at = datetime.now(timezone.utc) + timedelta(minutes=delay)
        self.db.commit()
        self.db.refresh(entity)
        return entity

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
