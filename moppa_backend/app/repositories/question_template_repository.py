from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.db.models import QuestionTemplateEntity
from app.models.question_template_model import QuestionTemplateCreateModel, QuestionTemplateUpdateModel


class QuestionTemplateRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, payload: QuestionTemplateCreateModel) -> QuestionTemplateEntity:
        entity = QuestionTemplateEntity(
            name=payload.name,
            level=payload.level,
            category=payload.category,
            template_content=payload.template_content,
            variables=payload.variables,
            generation_config=payload.generation_config,
            verification_conditions=payload.verification_conditions,
            duplicate_check_window=self._parse_interval(payload.duplicate_check_window),
            max_duplicate_rate=payload.max_duplicate_rate,
            status=payload.status,
            version=payload.version,
        )
        self.db.add(entity)
        self.db.flush()
        self.db.commit()
        self.db.refresh(entity)
        return entity

    def get_by_id(self, template_id: str) -> QuestionTemplateEntity | None:
        entity = self.db.get(QuestionTemplateEntity, UUID(template_id))
        if entity is None or entity.deleted_at is not None:
            return None
        return entity

    def list_paginated(self, page: int, page_size: int) -> tuple[list[QuestionTemplateEntity], int]:
        offset = (page - 1) * page_size
        base = select(QuestionTemplateEntity).where(QuestionTemplateEntity.deleted_at.is_(None))
        items = list(
            self.db.scalars(
                base.order_by(QuestionTemplateEntity.updated_at.desc()).offset(offset).limit(page_size)
            )
        )
        total = self.db.scalar(
            select(func.count()).select_from(QuestionTemplateEntity).where(QuestionTemplateEntity.deleted_at.is_(None))
        )
        return items, int(total or 0)

    def search_paginated(self, keyword: str, page: int, page_size: int) -> tuple[list[QuestionTemplateEntity], int]:
        offset = (page - 1) * page_size
        escaped = keyword.strip().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        pattern = f"%{escaped}%"
        filters = or_(
            QuestionTemplateEntity.name.ilike(pattern, escape="\\"),
            QuestionTemplateEntity.category.ilike(pattern, escape="\\"),
            QuestionTemplateEntity.template_content.ilike(pattern, escape="\\"),
        )
        base = select(QuestionTemplateEntity).where(QuestionTemplateEntity.deleted_at.is_(None), filters)
        items = list(
            self.db.scalars(
                base.order_by(QuestionTemplateEntity.updated_at.desc()).offset(offset).limit(page_size)
            )
        )
        total = self.db.scalar(
            select(func.count())
            .select_from(QuestionTemplateEntity)
            .where(QuestionTemplateEntity.deleted_at.is_(None), filters)
        )
        return items, int(total or 0)

    def list_all(self, keyword: str | None = None) -> list[QuestionTemplateEntity]:
        query = select(QuestionTemplateEntity).where(QuestionTemplateEntity.deleted_at.is_(None))
        if keyword and keyword.strip():
            escaped = keyword.strip().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            pattern = f"%{escaped}%"
            query = query.where(
                or_(
                    QuestionTemplateEntity.name.ilike(pattern, escape="\\"),
                    QuestionTemplateEntity.category.ilike(pattern, escape="\\"),
                    QuestionTemplateEntity.template_content.ilike(pattern, escape="\\"),
                )
            )
        return list(self.db.scalars(query.order_by(QuestionTemplateEntity.updated_at.desc())))

    def update(self, template_id: str, payload: QuestionTemplateUpdateModel) -> QuestionTemplateEntity | None:
        entity = self.get_by_id(template_id)
        if entity is None:
            return None

        if payload.name is not None:
            entity.name = payload.name
        if payload.level is not None:
            entity.level = payload.level
        if payload.category is not None:
            entity.category = payload.category
        if payload.template_content is not None:
            entity.template_content = payload.template_content
        if payload.variables is not None:
            entity.variables = payload.variables
        if payload.generation_config is not None:
            entity.generation_config = payload.generation_config
        if payload.verification_conditions is not None:
            entity.verification_conditions = payload.verification_conditions
        if payload.duplicate_check_window is not None:
            entity.duplicate_check_window = self._parse_interval(payload.duplicate_check_window)
        if payload.max_duplicate_rate is not None:
            entity.max_duplicate_rate = payload.max_duplicate_rate
        if payload.status is not None:
            entity.status = payload.status
        if payload.version is not None:
            entity.version = payload.version
        entity.updated_at = datetime.now(timezone.utc)

        self.db.commit()
        self.db.refresh(entity)
        return entity

    def batch_soft_delete(self, ids: list[str]) -> int:
        uuid_ids = [UUID(value) for value in ids]
        entities = list(self.db.scalars(select(QuestionTemplateEntity).where(QuestionTemplateEntity.id.in_(uuid_ids))))
        now = datetime.now(timezone.utc)
        changed = 0
        for entity in entities:
            if entity.deleted_at is None:
                entity.deleted_at = now
                entity.updated_at = now
                changed += 1
        self.db.commit()
        return changed

    def _parse_interval(self, value: str) -> timedelta:
        normalized = value.strip().lower()
        if normalized.endswith("days"):
            return timedelta(days=int(normalized.replace("days", "").strip()))
        if normalized.endswith("day"):
            return timedelta(days=int(normalized.replace("day", "").strip()))
        if normalized.endswith("hours"):
            return timedelta(hours=int(normalized.replace("hours", "").strip()))
        if normalized.endswith("hour"):
            return timedelta(hours=int(normalized.replace("hour", "").strip()))
        if normalized.endswith("minutes"):
            return timedelta(minutes=int(normalized.replace("minutes", "").strip()))
        if normalized.endswith("minute"):
            return timedelta(minutes=int(normalized.replace("minute", "").strip()))
        return timedelta(days=7)
