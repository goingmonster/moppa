from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import SystemConfigEntity


class TaskConfigRepository:
    KEY_PREFIX = "task."

    def __init__(self, db: Session) -> None:
        self.db = db

    def _key(self, task_type: str) -> str:
        return f"{self.KEY_PREFIX}{task_type}"

    def get_by_task_type(self, task_type: str) -> SystemConfigEntity | None:
        return self.db.scalar(select(SystemConfigEntity).where(SystemConfigEntity.key == self._key(task_type)))

    def list_paginated(self, page: int, page_size: int) -> tuple[list[SystemConfigEntity], int]:
        offset = (page - 1) * page_size
        items = list(
            self.db.scalars(
                select(SystemConfigEntity)
                .where(SystemConfigEntity.key.like(f"{self.KEY_PREFIX}%"))
                .order_by(SystemConfigEntity.updated_at.desc())
                .offset(offset)
                .limit(page_size)
            )
        )
        total = self.db.scalar(
            select(func.count()).select_from(SystemConfigEntity).where(SystemConfigEntity.key.like(f"{self.KEY_PREFIX}%"))
        )
        return items, int(total or 0)

    def create(self, task_type: str, value: dict[str, object], description: str | None) -> SystemConfigEntity:
        entity = SystemConfigEntity(
            key=self._key(task_type),
            value=value,
            description=description,
            category="task",
            is_sensitive=False,
        )
        self.db.add(entity)
        self.db.flush()
        self.db.commit()
        self.db.refresh(entity)
        return entity

    def update(self, task_type: str, value: dict[str, object] | None, description: str | None) -> SystemConfigEntity | None:
        entity = self.get_by_task_type(task_type)
        if entity is None:
            return None
        if value is not None:
            entity.value = value
        if description is not None:
            entity.description = description
        entity.updated_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(entity)
        return entity

    def delete(self, task_type: str) -> bool:
        entity = self.get_by_task_type(task_type)
        if entity is None:
            return False
        self.db.delete(entity)
        self.db.commit()
        return True
