from datetime import datetime

from sqlalchemy import JSON, TEXT, VARCHAR, DateTime, Index, Integer
from sqlalchemy.orm import Mapped, mapped_column

from models import Base
from models.mixins.serializer import SerializerMixin


class CrawlJob(Base, SerializerMixin):
    __tablename__ = "crawl_job"

    __table_args__ = (
        Index("ix_crawl_job_type_status", "job_type", "status"),
        Index("ix_crawl_job_subscription_id", "subscription_id"),
        Index("ix_crawl_job_site_priority", "site", "priority"),
        Index("ix_crawl_job_trace_id", "trace_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    job_type: Mapped[str] = mapped_column(VARCHAR(32), nullable=False)
    source_type: Mapped[str] = mapped_column(VARCHAR(32), nullable=False)
    site: Mapped[str | None] = mapped_column(VARCHAR(64), nullable=True)
    subscription_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(VARCHAR(16), nullable=False, default="pending")
    priority: Mapped[str] = mapped_column(VARCHAR(16), nullable=False, default="normal")
    trace_id: Mapped[str | None] = mapped_column(VARCHAR(64), nullable=True)
    payload: Mapped[dict | None] = mapped_column(JSON, nullable=True, default=dict)
    error_message: Mapped[str | None] = mapped_column(TEXT, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    def __init__(self, **kwargs):
        kwargs.setdefault("status", "pending")
        kwargs.setdefault("priority", "normal")
        kwargs.setdefault("payload", {})
        super().__init__(**kwargs)
