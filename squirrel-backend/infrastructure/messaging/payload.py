"""Pydantic schema for Message rows serialized onto the Redis Stream.

``Message.to_dict()`` was used to build the stream payload, exposing every
column. This schema makes the payload shape explicit (the full column set, for
wire-shape parity with the historical behavior) while removing the dependency
on ``SerializerMixin``.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_serializer

from infrastructure.http.serializers import serialize_datetime


class MessagePayload(BaseModel):
    """The shape of a Message row when published onto a Redis Stream."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    trace_id: str | None = None
    queue_name: str | None = None
    message_type: str | None = None
    body: str
    status: str = 'PENDING'
    error_msg: str | None = None
    retry_count: int = 0
    next_retry_time: datetime | None = None
    processed_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @field_serializer('next_retry_time', 'processed_at', 'created_at', 'updated_at')
    def _serialize_datetime(self, dt: datetime | None) -> str | None:
        return serialize_datetime(dt)


def serialize_message(message) -> dict:
    """Serialize a Message ORM row into its Redis Stream payload shape."""
    return MessagePayload.model_validate(message).model_dump()
