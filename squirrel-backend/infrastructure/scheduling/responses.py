"""Pydantic response schema for scheduled tasks.

Replaces ``ScheduledTask.to_dict()`` in the task list / create-task responses
with an explicit field set. The historical ``to_dict()`` exposed all 22 model
columns including ``task_params`` (arbitrary JSON), ``last_error`` text and
``created_by``/``updated_by`` audit fields; this schema keeps that same set
for wire-shape parity -- narrowing it is a deliberate API change that should
be coordinated with clients.
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, field_serializer

from infrastructure.http.serializers import serialize_datetime


class ScheduledTaskResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    task_type: str
    description: str | None = None
    interval: int
    unit: str
    start_immediately: bool
    max_retries: int
    status: str
    is_active: bool
    task_class: str
    task_params: dict[str, Any]
    last_run_at: datetime | None = None
    next_run_at: datetime | None = None
    last_error: str | None = None
    run_count: int = 0
    success_count: int = 0
    error_count: int = 0
    created_at: datetime | None = None
    updated_at: datetime | None = None
    created_by: str | None = None
    updated_by: str | None = None

    @field_serializer('last_run_at', 'next_run_at', 'created_at', 'updated_at')
    def _serialize_datetime(self, dt: datetime | None) -> str | None:
        return serialize_datetime(dt)


def serialize_scheduled_task(task) -> dict:
    """Serialize a ScheduledTask ORM row into its public response shape."""
    return ScheduledTaskResponse.model_validate(task).model_dump()
