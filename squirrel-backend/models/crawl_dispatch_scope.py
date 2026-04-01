from datetime import datetime

from sqlalchemy import DateTime, Integer, Index, UniqueConstraint, VARCHAR
from sqlalchemy.orm import Mapped, mapped_column

from models import Base
from models.mixins.serializer import SerializerMixin


class CrawlDispatchScope(Base, SerializerMixin):
    __tablename__ = 'crawl_dispatch_scope'

    __table_args__ = (
        UniqueConstraint('scope_type', 'scope_key', name='uq_crawl_dispatch_scope_type_key'),
        Index('ix_crawl_dispatch_scope_type_key', 'scope_type', 'scope_key'),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    scope_type: Mapped[str] = mapped_column(VARCHAR(32), nullable=False)
    scope_key: Mapped[str] = mapped_column(VARCHAR(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.now)
