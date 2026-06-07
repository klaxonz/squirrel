from datetime import datetime

from sqlalchemy import TEXT, VARCHAR, DateTime, Index, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from models import Base
from models.mixins.serializer import SerializerMixin


class VideoExtractionProjection(Base, SerializerMixin):
    __tablename__ = "video_extraction_projection"

    __table_args__ = (
        UniqueConstraint(
            "subscription_id",
            "group_kind",
            "group_value",
            name="uix_video_extraction_projection_group",
        ),
        Index("ix_video_extraction_projection_subscription_id", "subscription_id"),
        Index("ix_video_extraction_projection_display_status", "display_status"),
        Index("ix_video_extraction_projection_updated_at", "updated_at"),
        Index(
            "ix_video_extraction_projection_status_updated",
            "display_status",
            "updated_at",
        ),
        Index(
            "ix_video_extraction_projection_status_queued_at",
            "display_status",
            "queued_at",
        ),
        Index(
            "ix_video_extraction_projection_status_locked_at",
            "display_status",
            "locked_at",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    subscription_id: Mapped[int] = mapped_column(Integer, nullable=False)
    group_kind: Mapped[str] = mapped_column(VARCHAR(16), nullable=False)
    group_value: Mapped[str] = mapped_column(VARCHAR(64), nullable=False)
    site: Mapped[str | None] = mapped_column(VARCHAR(64), nullable=True)
    sync_status: Mapped[str] = mapped_column(VARCHAR(16), nullable=False, default="idle")
    display_status: Mapped[str] = mapped_column(VARCHAR(16), nullable=False, default="healthy")
    current_phase: Mapped[str | None] = mapped_column(VARCHAR(32), nullable=True)
    last_error: Mapped[str | None] = mapped_column(TEXT, nullable=True)
    queued_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    locked_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_success_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    pending_video_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    batch_task_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    queued_task_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    running_task_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    completed_task_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    failed_task_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)
