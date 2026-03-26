from datetime import datetime, timezone
import json
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session


class PredictionRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_existing(self, question_id: UUID, model_id: UUID) -> dict[str, object] | None:
        try:
            row = self.db.execute(
                text(
                    """
                    SELECT id, version, question_id, model_id, prediction_content,
                           confidence, inference_time_ms, token_usage, source_system,
                           trace_id, task_execution_id, status, error_message,
                           submission_time, created_at, updated_at, deleted_at
                    FROM prediction
                    WHERE question_id = :question_id
                      AND model_id = :model_id
                      AND deleted_at IS NULL
                    """
                ),
                {"question_id": str(question_id), "model_id": str(model_id)},
            ).mappings().first()
            return dict(row) if row else None
        except SQLAlchemyError:
            self.db.rollback()
            raise

    def upsert(
        self,
        question_id: UUID,
        model_id: UUID,
        prediction_content: str,
        confidence: float | None,
        inference_time_ms: int | None,
        token_usage: dict[str, object],
        trace_id: UUID,
        task_execution_id: UUID | None,
        status: str = "completed",
        error_message: str | None = None,
    ) -> dict[str, object]:
        now = datetime.now(timezone.utc)
        token_usage_json = json.dumps(token_usage, ensure_ascii=False)
        try:
            existing = self.get_existing(question_id, model_id)
            if existing is not None:
                self.db.execute(
                    text(
                        """
                        UPDATE prediction
                        SET prediction_content = :prediction_content,
                            confidence = :confidence,
                            inference_time_ms = :inference_time_ms,
                            token_usage = CAST(:token_usage AS jsonb),
                            status = :status,
                            error_message = :error_message,
                            submission_time = :submission_time,
                            updated_at = :updated_at
                        WHERE id = :id
                        """
                    ),
                    {
                        "id": str(existing["id"]),
                        "prediction_content": prediction_content,
                        "confidence": confidence,
                        "inference_time_ms": inference_time_ms,
                        "token_usage": token_usage_json,
                        "status": status,
                        "error_message": error_message,
                        "submission_time": now,
                        "updated_at": now,
                    },
                )
                self.db.commit()
                row = self.db.execute(
                    text(
                        """
                        SELECT id, version, question_id, model_id, prediction_content,
                               confidence, inference_time_ms, token_usage, source_system,
                               trace_id, task_execution_id, status, error_message,
                               submission_time, created_at, updated_at, deleted_at
                        FROM prediction WHERE id = :id
                        """
                    ),
                    {"id": str(existing["id"])},
                ).mappings().first()
                return dict(row) if row else dict(existing)

            row = self.db.execute(
                text(
                    """
                    INSERT INTO prediction (
                        question_id, model_id, prediction_content, confidence,
                        inference_time_ms, token_usage, trace_id,
                        task_execution_id, status, error_message, submission_time
                    )
                    VALUES (
                        :question_id, :model_id, :prediction_content, :confidence,
                        :inference_time_ms, CAST(:token_usage AS jsonb), :trace_id,
                        :task_execution_id, :status, :error_message, :submission_time
                    )
                    RETURNING id, version, question_id, model_id, prediction_content,
                              confidence, inference_time_ms, token_usage, source_system,
                              trace_id, task_execution_id, status, error_message,
                              submission_time, created_at, updated_at, deleted_at
                    """
                ),
                {
                    "question_id": str(question_id),
                    "model_id": str(model_id),
                    "prediction_content": prediction_content,
                    "confidence": confidence,
                    "inference_time_ms": inference_time_ms,
                    "token_usage": token_usage_json,
                    "trace_id": str(trace_id),
                    "task_execution_id": str(task_execution_id) if task_execution_id else None,
                    "status": status,
                    "error_message": error_message,
                    "submission_time": now,
                },
            ).mappings().one()
            self.db.commit()
            return dict(row)
        except SQLAlchemyError:
            self.db.rollback()
            raise

    def list_by_question(self, question_id: UUID) -> list[dict[str, object]]:
        try:
            rows = self.db.execute(
                text(
                    """
                    SELECT
                        p.id, p.version, p.question_id, p.model_id, p.prediction_content,
                        p.confidence, p.inference_time_ms, p.token_usage,
                        p.status, p.error_message, p.submission_time, p.created_at,
                        me.name AS model_name, me.identifier AS model_identifier
                    FROM prediction p
                    JOIN model_endpoint me ON me.id = p.model_id
                    WHERE p.question_id = :question_id
                      AND p.deleted_at IS NULL
                    ORDER BY p.created_at DESC
                    """
                ),
                {"question_id": str(question_id)},
            ).mappings().all()
            return [dict(row) for row in rows]
        except SQLAlchemyError:
            self.db.rollback()
            raise
