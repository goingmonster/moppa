from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import delete, func, literal_column, select, text
from sqlalchemy.orm import Session

from app.db.models import QuestionEntity, QuestionEventEntity
from app.models.question_model import QuestionCreateModel, QuestionUpdateModel


class QuestionRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, payload: QuestionCreateModel) -> str:
        event_ids = self._resolve_event_ids(payload.event_ids, payload.event_id)

        entity = QuestionEntity(
            event_id=event_ids[0] if event_ids else None,
            template_id=payload.template_id,
            level=payload.level,
            content=payload.content,
            match_score=payload.match_score,
            event_domain=payload.event_domain,
            event_type=payload.event_type,
            area=payload.area,
            input_type=payload.input_type,
            background=payload.background,
            answer_space=payload.answer_space,
            verification_conditions=payload.verification_conditions,
            deadline=payload.deadline,
            trace_id=payload.trace_id,
            status=self._normalize_status(payload.status or "draft"),
        )
        self.db.add(entity)
        self.db.flush()
        if event_ids:
            self._replace_question_events(entity.id, event_ids)
        self.db.commit()
        return str(entity.id)

    def list_paginated(
        self,
        page: int,
        page_size: int,
        *,
        event_domain: str = "",
        event_type: str = "",
        status: str = "",
        level: int | None = None,
        created_from: datetime | None = None,
        created_to: datetime | None = None,
        deleted_mode: str = "active_only",
    ) -> tuple[list[QuestionEntity], int]:
        offset = (page - 1) * page_size
        base_query = select(QuestionEntity)
        count_query = select(func.count()).select_from(QuestionEntity)
        base_query, count_query = self._apply_manage_filters(
            base_query=base_query,
            count_query=count_query,
            keyword="",
            event_domain=event_domain,
            event_type=event_type,
            status=status,
            level=level,
            created_from=created_from,
            created_to=created_to,
            deleted_mode=deleted_mode,
        )
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

    def search_paginated(
        self,
        keyword: str,
        page: int,
        page_size: int,
        *,
        event_domain: str = "",
        event_type: str = "",
        status: str = "",
        level: int | None = None,
        created_from: datetime | None = None,
        created_to: datetime | None = None,
        deleted_mode: str = "active_only",
    ) -> tuple[list[QuestionEntity], int]:
        offset = (page - 1) * page_size
        base_query = select(QuestionEntity)
        count_query = select(func.count()).select_from(QuestionEntity)
        base_query, count_query = self._apply_manage_filters(
            base_query=base_query,
            count_query=count_query,
            keyword=keyword,
            event_domain=event_domain,
            event_type=event_type,
            status=status,
            level=level,
            created_from=created_from,
            created_to=created_to,
            deleted_mode=deleted_mode,
        )

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

    def _apply_manage_filters(
        self,
        *,
        base_query,
        count_query,
        keyword: str,
        event_domain: str,
        event_type: str,
        status: str,
        level: int | None,
        created_from: datetime | None,
        created_to: datetime | None,
        deleted_mode: str,
    ):
        normalized_deleted_mode = deleted_mode.strip().lower()
        if normalized_deleted_mode == "active_only":
            base_query = base_query.where(QuestionEntity.deleted_at.is_(None))
            count_query = count_query.where(QuestionEntity.deleted_at.is_(None))
        elif normalized_deleted_mode == "deleted_only":
            base_query = base_query.where(QuestionEntity.deleted_at.is_not(None))
            count_query = count_query.where(QuestionEntity.deleted_at.is_not(None))
        elif normalized_deleted_mode == "with_deleted":
            pass
        else:
            raise ValueError(f"invalid deleted mode: {deleted_mode}")

        normalized_keyword = keyword.strip()
        if normalized_keyword:
            escaped = normalized_keyword.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            pattern = f"%{escaped}%"
            filters = (
                QuestionEntity.content.ilike(pattern, escape="\\"),
                QuestionEntity.background.ilike(pattern, escape="\\"),
                QuestionEntity.answer_space.ilike(pattern, escape="\\"),
                QuestionEntity.event_domain.ilike(pattern, escape="\\"),
                QuestionEntity.event_type.ilike(pattern, escape="\\"),
                QuestionEntity.area.ilike(pattern, escape="\\"),
                QuestionEntity.input_type.ilike(pattern, escape="\\"),
                QuestionEntity.delete_reason.ilike(pattern, escape="\\"),
            )
            keyword_clause = filters[0]
            for clause in filters[1:]:
                keyword_clause = keyword_clause | clause
            base_query = base_query.where(keyword_clause)
            count_query = count_query.where(keyword_clause)

        normalized_event_domain = event_domain.strip()
        if normalized_event_domain:
            escaped = normalized_event_domain.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            pattern = f"%{escaped}%"
            base_query = base_query.where(QuestionEntity.event_domain.ilike(pattern, escape="\\"))
            count_query = count_query.where(QuestionEntity.event_domain.ilike(pattern, escape="\\"))

        normalized_event_type = event_type.strip()
        if normalized_event_type:
            escaped = normalized_event_type.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            pattern = f"%{escaped}%"
            base_query = base_query.where(QuestionEntity.event_type.ilike(pattern, escape="\\"))
            count_query = count_query.where(QuestionEntity.event_type.ilike(pattern, escape="\\"))

        normalized_status = status.strip()
        if normalized_status:
            lowered_status = normalized_status.lower()
            status_group_map = {
                "collecting": ["draft"],
                "locked": ["pending_review", "published", "expired", "matched"],
                "resolved": ["closed"],
            }
            grouped_statuses = status_group_map.get(lowered_status)
            if grouped_statuses is not None:
                base_query = base_query.where(QuestionEntity.status.in_(grouped_statuses))
                count_query = count_query.where(QuestionEntity.status.in_(grouped_statuses))
            else:
                resolved_status = self._normalize_status(normalized_status)
                base_query = base_query.where(QuestionEntity.status == resolved_status)
                count_query = count_query.where(QuestionEntity.status == resolved_status)

        if level is not None:
            base_query = base_query.where(QuestionEntity.level == level)
            count_query = count_query.where(QuestionEntity.level == level)

        if created_from is not None:
            base_query = base_query.where(QuestionEntity.created_at >= created_from)
            count_query = count_query.where(QuestionEntity.created_at >= created_from)

        if created_to is not None:
            base_query = base_query.where(QuestionEntity.created_at <= created_to)
            count_query = count_query.where(QuestionEntity.created_at <= created_to)

        return base_query, count_query

    def update(self, question_id: str, payload: QuestionUpdateModel) -> QuestionEntity | None:
        entity = self.get_by_id(question_id)
        if entity is None:
            return None

        if payload.level is not None:
            entity.level = payload.level
        if payload.content is not None:
            entity.content = payload.content
        if payload.match_score is not None:
            entity.match_score = payload.match_score
        if payload.event_domain is not None:
            entity.event_domain = payload.event_domain
        if payload.event_type is not None:
            entity.event_type = payload.event_type
        if payload.area is not None:
            entity.area = payload.area
        if payload.input_type is not None:
            entity.input_type = payload.input_type
        if payload.background is not None:
            entity.background = payload.background
        if payload.answer_space is not None:
            entity.answer_space = payload.answer_space
        if payload.deadline is not None:
            entity.deadline = payload.deadline
        if payload.status is not None:
            entity.status = self._normalize_status(payload.status)
        if payload.event_ids is not None:
            event_ids = self._resolve_event_ids(payload.event_ids, None)
            entity.event_id = event_ids[0] if event_ids else None
            self._replace_question_events(entity.id, event_ids)

        self.db.commit()
        self.db.refresh(entity)
        return entity

    def batch_soft_delete(self, ids: list[str], delete_reason: str) -> int:
        uuid_ids = [UUID(value) for value in ids]
        entities = list(self.db.scalars(select(QuestionEntity).where(QuestionEntity.id.in_(uuid_ids))))
        now = datetime.now(timezone.utc)
        normalized_reason = delete_reason.strip()
        changed = 0
        for entity in entities:
            if entity.deleted_at is None:
                entity.deleted_at = now
                entity.delete_reason = normalized_reason
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

    def get_coordinates_map(self, question_ids: list[str]) -> dict[str, dict[str, float]]:
        if not question_ids:
            return {}
        uuid_ids = [UUID(value) for value in question_ids]
        rows = self.db.execute(
            select(
                QuestionEntity.id,
                literal_column("question.coordinates[1]").label("latitude"),
                literal_column("question.coordinates[0]").label("longitude"),
            ).where(QuestionEntity.id.in_(uuid_ids))
        )

        result: dict[str, dict[str, float]] = {}
        for question_id, latitude, longitude in rows:
            if latitude is None or longitude is None:
                continue
            result[str(question_id)] = {
                "latitude": float(latitude),
                "longitude": float(longitude),
            }
        return result

    def count_without_coordinates(
        self,
        range_start: datetime | None,
        range_end: datetime | None,
    ) -> int:
        query = """
            SELECT COUNT(*)
            FROM question
            WHERE deleted_at IS NULL
              AND coordinates IS NULL
        """
        params: dict[str, object] = {}
        if range_start is not None:
            query += "\n  AND created_at >= :range_start"
            params["range_start"] = range_start
        if range_end is not None:
            query += "\n  AND created_at < :range_end"
            params["range_end"] = range_end

        total = self.db.execute(text(query), params).scalar_one()
        return int(total)

    def list_without_coordinates(
        self,
        range_start: datetime | None,
        range_end: datetime | None,
    ) -> list[dict[str, object]]:
        query = """
            SELECT id, area, content, created_at
            FROM question
            WHERE deleted_at IS NULL
              AND coordinates IS NULL
        """
        params: dict[str, object] = {}
        if range_start is not None:
            query += "\n  AND created_at >= :range_start"
            params["range_start"] = range_start
        if range_end is not None:
            query += "\n  AND created_at < :range_end"
            params["range_end"] = range_end
        query += "\nORDER BY created_at ASC"

        rows = self.db.execute(text(query), params).mappings().all()
        return [dict(row) for row in rows]

    def update_coordinates(self, question_id: UUID, latitude: float, longitude: float) -> bool:
        now = datetime.now(timezone.utc)
        result = self.db.execute(
            text(
                """
                UPDATE question
                SET coordinates = point(:longitude, :latitude),
                    updated_at = :updated_at
                WHERE id = :question_id
                  AND deleted_at IS NULL
                  AND coordinates IS NULL
                """
            ),
            {
                "question_id": str(question_id),
                "longitude": float(longitude),
                "latitude": float(latitude),
                "updated_at": now,
            },
        )
        self.db.commit()
        rowcount = getattr(result, "rowcount", 0)
        return int(rowcount or 0) > 0

    def _replace_question_events(self, question_id: UUID, event_ids: list[UUID]) -> None:
        _ = self.db.execute(delete(QuestionEventEntity).where(QuestionEventEntity.question_id == question_id))
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
        normalized = value.strip().lower()
        mapping = {
            "collecting": "draft",
            "locked": "pending_review",
            "resolved": "closed",
            "draft": "draft",
            "pending_review": "pending_review",
            "published": "published",
            "closed": "closed",
            "expired": "expired",
            "matched": "matched",
        }
        resolved = mapping.get(normalized)
        if resolved is None:
            raise ValueError(f"invalid question status: {value}")
        return resolved
