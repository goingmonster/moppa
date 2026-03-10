from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, Integer, String, Text, func, text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class EventEntity(Base):
    __tablename__ = "event"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    event_key: Mapped[str] = mapped_column(String(255))
    content: Mapped[str] = mapped_column(Text)
    source_system: Mapped[str] = mapped_column(String(100))
    credibility_level: Mapped[int] = mapped_column(Integer)
    event_time: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    filter_status: Mapped[str] = mapped_column(String(20))
    trace_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True))
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class QuestionEntity(Base):
    __tablename__ = "question"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    event_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True))
    level: Mapped[int] = mapped_column(Integer)
    content: Mapped[str] = mapped_column(Text)
    deadline: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(20))
    trace_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True))
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class TaskExecutionEntity(Base):
    __tablename__ = "task_execution"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    task_type: Mapped[str] = mapped_column(String(50))
    idempotency_key: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20))
    attempt_count: Mapped[int] = mapped_column(Integer, server_default=text("0"))
    trace_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
