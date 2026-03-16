from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import AppUserEntity, FeedbackEntity


class QuestionCommentRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_by_question(self, question_id: UUID) -> list[tuple[FeedbackEntity, str]]:
        rows = list(
            self.db.execute(
                select(FeedbackEntity, AppUserEntity.username)
                .join(AppUserEntity, AppUserEntity.id == FeedbackEntity.user_id)
                .where(
                    FeedbackEntity.feedback_type == "comment",
                    FeedbackEntity.target_type == "question",
                    FeedbackEntity.target_id == question_id,
                    FeedbackEntity.deleted_at.is_(None),
                    AppUserEntity.deleted_at.is_(None),
                )
                .order_by(FeedbackEntity.created_at.desc())
            )
        )
        return [(entity, username) for entity, username in rows]

    def get_by_id(self, comment_id: UUID) -> FeedbackEntity | None:
        entity = self.db.get(FeedbackEntity, comment_id)
        if entity is None or entity.deleted_at is not None:
            return None
        if entity.feedback_type != "comment" or entity.target_type != "question":
            return None
        return entity

    def create(
        self,
        question_id: UUID,
        user_id: UUID,
        content: str,
        trace_id: UUID,
    ) -> FeedbackEntity:
        entity = FeedbackEntity(
            feedback_type="comment",
            target_type="question",
            target_id=question_id,
            user_id=user_id,
            content=content,
            status="open",
            priority="normal",
            trace_id=trace_id,
        )
        self.db.add(entity)
        self.db.commit()
        self.db.refresh(entity)
        return entity

    def update_content(self, entity: FeedbackEntity, content: str) -> FeedbackEntity:
        entity.content = content
        entity.updated_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(entity)
        return entity

    def soft_delete(self, entity: FeedbackEntity) -> None:
        now = datetime.now(timezone.utc)
        entity.deleted_at = now
        entity.updated_at = now
        self.db.commit()
