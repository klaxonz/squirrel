from datetime import datetime

from sqlalchemy import VARCHAR, DateTime, Index, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from infrastructure.database.base import Base


class CrawlDispatchScope(Base):
    __tablename__ = 'crawl_dispatch_scope'

    __table_args__ = (
        UniqueConstraint('scope_type', 'scope_key', name='uq_crawl_dispatch_scope_type_key'),
        Index('ix_crawl_dispatch_scope_type_key', 'scope_type', 'scope_key'),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    scope_type: Mapped[str] = mapped_column(VARCHAR(32), nullable=False)
    scope_key: Mapped[str] = mapped_column(VARCHAR(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.now)
