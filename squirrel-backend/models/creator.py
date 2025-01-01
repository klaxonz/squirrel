from datetime import datetime
from typing import Optional

from sqlalchemy.types import JSON
from sqlmodel import Field, SQLModel


class Creator(SQLModel, table=True):
    __tablename__ = "creator"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    url: Optional[str] = Field(sa_column_kwargs={"unique": True})
    avatar: Optional[str]
    description: Optional[str]
    is_deleted: bool = Field(default=False)
    extra_data: Optional[dict] = Field(default=None, sa_type=JSON)
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(),
        sa_column_kwargs={"onupdate": lambda: datetime.now()}
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now()
    )

