from datetime import datetime

from sqlalchemy import JSON, TEXT, VARCHAR, DateTime, Index, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from shared_kernel.domain.base import Base
from shared_kernel.domain.mixins import SerializerMixin


class OutboxEvent(Base, SerializerMixin):
    __tablename__ = "outbox_event"

    __table_args__ = (
        UniqueConstraint("event_key", name="uix_outbox_event_event_key"),
        Index("ix_outbox_event_status_available", "status", "available_at"),
        Index("ix_outbox_event_aggregate_lookup", "aggregate_type", "aggregate_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    event_type: Mapped[str] = mapped_column(VARCHAR(64), nullable=False)
    event_key: Mapped[str] = mapped_column(VARCHAR(255), nullable=False)
    aggregate_type: Mapped[str] = mapped_column(VARCHAR(64), nullable=False)
    aggregate_id: Mapped[str] = mapped_column(VARCHAR(64), nullable=False)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    status: Mapped[str] = mapped_column(VARCHAR(16), nullable=False, default="pending")
    priority: Mapped[str] = mapped_column(VARCHAR(16), nullable=False, default="normal")
    available_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.now)
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    max_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    locked_by: Mapped[str | None] = mapped_column(VARCHAR(64), nullable=True)
    locked_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_error: Mapped[str | None] = mapped_column(TEXT, nullable=True)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)
