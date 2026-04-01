from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Index, Integer, JSON, TEXT, VARCHAR
from sqlalchemy.orm import Mapped, mapped_column

from models import Base
from models.mixins.serializer import SerializerMixin


class CrawlTask(Base, SerializerMixin):
    __tablename__ = 'crawl_task'

    __table_args__ = (
        Index('ix_crawl_task_runnable_lookup', 'status', 'next_run_at', 'priority', 'site'),
        Index('ix_crawl_task_lease_until', 'lease_until'),
        Index('ix_crawl_task_site_status', 'site', 'status'),
        Index('ix_crawl_task_job_id', 'job_id'),
        Index('ix_crawl_task_parent_task_id', 'parent_task_id'),
        Index('ix_crawl_task_type_status', 'task_type', 'status'),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    job_id: Mapped[int] = mapped_column(ForeignKey('crawl_job.id'), nullable=False)
    parent_task_id: Mapped[Optional[int]] = mapped_column(ForeignKey('crawl_task.id'), nullable=True)
    task_type: Mapped[str] = mapped_column(VARCHAR(32), nullable=False)
    site: Mapped[str] = mapped_column(VARCHAR(64), nullable=False)
    subscription_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    video_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    video_url: Mapped[Optional[str]] = mapped_column(VARCHAR(2048), nullable=True)
    status: Mapped[str] = mapped_column(VARCHAR(16), nullable=False, default='pending')
    priority: Mapped[str] = mapped_column(VARCHAR(16), nullable=False, default='normal')
    payload: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    dedupe_key: Mapped[Optional[str]] = mapped_column(VARCHAR(255), nullable=True, unique=True)
    attempt: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    max_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    next_run_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.now)
    lease_until: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    worker_id: Mapped[Optional[str]] = mapped_column(VARCHAR(128), nullable=True)
    last_error: Mapped[Optional[str]] = mapped_column(TEXT, nullable=True)
    last_error_type: Mapped[Optional[str]] = mapped_column(VARCHAR(128), nullable=True)
    trace_id: Mapped[Optional[str]] = mapped_column(VARCHAR(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    def __init__(self, **kwargs):
        kwargs.setdefault('status', 'pending')
        kwargs.setdefault('priority', 'normal')
        kwargs.setdefault('payload', {})
        kwargs.setdefault('attempt', 0)
        kwargs.setdefault('max_attempts', 3)
        kwargs.setdefault('next_run_at', datetime.now())
        super().__init__(**kwargs)
