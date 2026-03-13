from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.db.models import QuestionEntity, QuestionEventEntity
from app.models.question_model import QuestionCreateModel, QuestionUpdateModel


class QuestionRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, payload: QuestionCreateModel) -> str:
        event_ids = self._resolve_event_ids(payload.event_ids, payload.event_id)
        if not event_ids:
            raise ValueError("event_ids is required")

        entity = QuestionEntity(
            event_id=event_ids[0],
            level=payload.level,
            content=payload.content,
            answer_space=payload.answer_space,
            deadline=payload.deadline,
            trace_id=payload.trace_id,
            status="draft",
        )
        self.db.add(entity)
        self.db.flush()
        self._replace_question_events(entity.id, event_ids)
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

        if payload.level is not None:
            entity.level = payload.level
        if payload.content is not None:
            entity.content = payload.content
        if payload.answer_space is not None:
            entity.answer_space = payload.answer_space
        if payload.deadline is not None:
            entity.deadline = payload.deadline
        if payload.status is not None:
            entity.status = self._normalize_status(payload.status)
        if payload.event_ids is not None:
            event_ids = self._resolve_event_ids(payload.event_ids, None)
            if not event_ids:
                raise ValueError("event_ids cannot be empty")
            entity.event_id = event_ids[0]
            self._replace_question_events(entity.id, event_ids)

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

    def get_event_ids_map(self, question_ids: list[str]) -> dict[str, list[str]]:
        if not question_ids:
            return {}
        uuid_ids = [UUID(value) for value in question_ids]
        rows = list(
            self.db.execute(
                select(QuestionEventEntity.question_id, QuestionEventEntity.event_id).where(
                    QuestionEventEntity.question_id.in_(uuid_ids)
                )
            )
        )
        result: dict[str, list[str]] = {value: [] for value in question_ids}
        for question_id, event_id in rows:
            result.setdefault(str(question_id), []).append(str(event_id))
        return result

    def get_event_ids(self, question_id: str) -> list[str]:
        rows = list(
            self.db.scalars(
                select(QuestionEventEntity.event_id).where(QuestionEventEntity.question_id == UUID(question_id))
            )
        )
        return [str(value) for value in rows]

    def _replace_question_events(self, question_id: UUID, event_ids: list[UUID]) -> None:
        self.db.execute(delete(QuestionEventEntity).where(QuestionEventEntity.question_id == question_id))
        for event_id in event_ids:
            self.db.add(QuestionEventEntity(question_id=question_id, event_id=event_id))

    @staticmethod
    def _resolve_event_ids(event_ids: list[UUID] | None, fallback_event_id: UUID | None) -> list[UUID]:
        if event_ids and len(event_ids) > 0:
            return list(dict.fromkeys(event_ids))
        if fallback_event_id is not None:
            return [fallback_event_id]
        return []

    @staticmethod
    def _normalize_status(value: str) -> str:
        normalized = value.strip()
        mapping = {
            "collecting": "draft",
            "locked": "pending_review",
            "resolved": "closed",
            "draft": "draft",
            "pending_review": "pending_review",
            "published": "published",
            "closed": "closed",
            "expired": "expired",
        }
        resolved = mapping.get(normalized)
        if resolved is None:
            raise ValueError(f"invalid question status: {value}")
        return resolved
