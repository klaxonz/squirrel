from datetime import datetime
from enum import Enum
from typing import Optional

from sqlalchemy import Integer, DateTime, Boolean, VARCHAR, JSON
from sqlalchemy.orm import mapped_column, Mapped
from models import Base
from models.mixins.serializer import SerializerMixin


class User(Base, SerializerMixin):
    __tablename__ = 'user'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nickname: Mapped[str] = mapped_column(VARCHAR(50), nullable=False)
    avatar: Mapped[Optional[str]] = mapped_column(VARCHAR(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(),
        onupdate=lambda: datetime.now()
    )


class AccountType(str, Enum):
    EMAIL = 'email'


class Account(Base, SerializerMixin):
    __tablename__ = 'account'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False)
    account_type: Mapped[str] = mapped_column(VARCHAR(20), nullable=False)
    identifier: Mapped[str] = mapped_column(VARCHAR(120), unique=True, nullable=False)
    credential: Mapped[str] = mapped_column(VARCHAR(128))
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    last_login_at: Mapped[datetime] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(),
        onupdate=lambda: datetime.now()
    )


class UserConfig(Base, SerializerMixin):
    __tablename__ = 'user_config'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False)
    settings: Mapped[dict] = mapped_column(JSON, nullable=False, default={})
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now())
    updated_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(), onupdate=lambda: datetime.now())

