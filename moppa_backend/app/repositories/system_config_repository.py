from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import SystemConfigEntity


class SystemConfigRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_key(self, key: str) -> SystemConfigEntity | None:
        return self.db.scalar(select(SystemConfigEntity).where(SystemConfigEntity.key == key))

    def get_value(self, key: str) -> dict[str, object] | None:
        entity = self.get_by_key(key)
        if entity is None:
            return None
        return entity.value

    def upsert_value(
        self,
        key: str,
        value: dict[str, object],
        description: str | None = None,
        category: str | None = None,
    ) -> SystemConfigEntity:
        entity = self.get_by_key(key)
        now = datetime.now(timezone.utc)
        if entity is None:
            entity = SystemConfigEntity(
                key=key,
                value=value,
                description=description,
                category=category,
                is_sensitive=False,
            )
            self.db.add(entity)
        else:
            entity.value = value
            if description is not None:
                entity.description = description
            if category is not None:
                entity.category = category
            entity.updated_at = now
        self.db.flush()
        self.db.commit()
        self.db.refresh(entity)
        return entity
