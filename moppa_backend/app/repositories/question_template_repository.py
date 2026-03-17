from datetime import datetime, timezone
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
            template_index=payload.template_index,
            question_template=payload.question_template,
            difficulty_level=payload.difficulty_level,
            candidate_answer_type=payload.candidate_answer_type,
            event_domain=payload.event_domain,
            event_type=payload.event_type,
            event_type_id=payload.event_type_id,
            operation_level=payload.operation_level,
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
            QuestionTemplateEntity.question_template.ilike(pattern, escape="\\"),
            QuestionTemplateEntity.candidate_answer_type.ilike(pattern, escape="\\"),
            QuestionTemplateEntity.event_domain.ilike(pattern, escape="\\"),
            QuestionTemplateEntity.event_type.ilike(pattern, escape="\\"),
            QuestionTemplateEntity.event_type_id.ilike(pattern, escape="\\"),
            QuestionTemplateEntity.operation_level.ilike(pattern, escape="\\"),
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
                    QuestionTemplateEntity.question_template.ilike(pattern, escape="\\"),
                    QuestionTemplateEntity.candidate_answer_type.ilike(pattern, escape="\\"),
                    QuestionTemplateEntity.event_domain.ilike(pattern, escape="\\"),
                    QuestionTemplateEntity.event_type.ilike(pattern, escape="\\"),
                    QuestionTemplateEntity.event_type_id.ilike(pattern, escape="\\"),
                    QuestionTemplateEntity.operation_level.ilike(pattern, escape="\\"),
                )
            )
        return list(self.db.scalars(query.order_by(QuestionTemplateEntity.updated_at.desc())))

    def update(self, template_id: str, payload: QuestionTemplateUpdateModel) -> QuestionTemplateEntity | None:
        entity = self.get_by_id(template_id)
        if entity is None:
            return None

        if payload.template_index is not None:
            entity.template_index = payload.template_index
        if payload.question_template is not None:
            entity.question_template = payload.question_template
        if payload.difficulty_level is not None:
            entity.difficulty_level = payload.difficulty_level
        if payload.candidate_answer_type is not None:
            entity.candidate_answer_type = payload.candidate_answer_type
        if payload.event_domain is not None:
            entity.event_domain = payload.event_domain
        if payload.event_type is not None:
            entity.event_type = payload.event_type
        if payload.event_type_id is not None:
            entity.event_type_id = payload.event_type_id
        if payload.operation_level is not None:
            entity.operation_level = payload.operation_level
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
