from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import QuestionEntity
from app.models.question_model import QuestionCreateModel, QuestionUpdateModel


class QuestionRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, payload: QuestionCreateModel) -> str:
        entity = QuestionEntity(
            event_id=payload.event_id,
            level=payload.level,
            content=payload.content,
            deadline=payload.deadline,
            trace_id=payload.trace_id,
            status="draft",
        )
        self.db.add(entity)
        self.db.flush()
        self.db.commit()
        return str(entity.id)

    def list_paginated(self, page: int, page_size: int) -> tuple[list[QuestionEntity], int]:
        offset = (page - 1) * page_size
        items = list(
            self.db.scalars(
                select(QuestionEntity)
                .where(QuestionEntity.deleted_at.is_(None))
                .order_by(QuestionEntity.created_at.desc())
                .offset(offset)
                .limit(page_size)
            )
        )
        total = self.db.scalar(
            select(func.count()).select_from(QuestionEntity).where(QuestionEntity.deleted_at.is_(None))
        )
        return items, int(total or 0)

    def search_paginated(self, keyword: str, page: int, page_size: int) -> tuple[list[QuestionEntity], int]:
        offset = (page - 1) * page_size
        base_query = select(QuestionEntity).where(QuestionEntity.deleted_at.is_(None))
        count_query = select(func.count()).select_from(QuestionEntity).where(QuestionEntity.deleted_at.is_(None))

        normalized = keyword.strip()
        if normalized:
            escaped = normalized.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            pattern = f"%{escaped}%"
            base_query = base_query.where(QuestionEntity.content.ilike(pattern, escape="\\"))
            count_query = count_query.where(QuestionEntity.content.ilike(pattern, escape="\\"))

        items = list(
            self.db.scalars(
                base_query
                .order_by(QuestionEntity.created_at.desc())
                .offset(offset)
                .limit(page_size)
            )
        )
        total = self.db.scalar(count_query)
        return items, int(total or 0)

    def get_by_id(self, question_id: str) -> QuestionEntity | None:
        entity = self.db.get(QuestionEntity, UUID(question_id))
        if entity is None or entity.deleted_at is not None:
            return None
        return entity

    def update(self, question_id: str, payload: QuestionUpdateModel) -> QuestionEntity | None:
        entity = self.get_by_id(question_id)
        if entity is None:
            return None

        if payload.content is not None:
            entity.content = payload.content
        if payload.deadline is not None:
            entity.deadline = payload.deadline
        if payload.status is not None:
            entity.status = payload.status

        self.db.commit()
        self.db.refresh(entity)
        return entity

    def batch_soft_delete(self, ids: list[str]) -> int:
        uuid_ids = [UUID(value) for value in ids]
        entities = list(self.db.scalars(select(QuestionEntity).where(QuestionEntity.id.in_(uuid_ids))))
        now = datetime.now(timezone.utc)
        changed = 0
        for entity in entities:
            if entity.deleted_at is None:
                entity.deleted_at = now
                changed += 1
        self.db.commit()
        return changed
