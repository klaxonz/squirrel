import json
from datetime import datetime
from typing import Any

from pydantic import ConfigDict, field_serializer, model_validator
from sqlalchemy_to_pydantic import sqlalchemy_to_pydantic

from domains.subscription.domain.models.subscription import Subscription


def _subscription_schema_extra(schema: dict[str, Any]) -> None:
    if 'properties' in schema and 'extra_data' in schema['properties']:
        schema['properties']['extra_data']['type'] = ['object', 'string', 'null']


class SubscriptionDto(sqlalchemy_to_pydantic(Subscription)):
    model_config = ConfigDict(from_attributes=True, json_schema_extra=_subscription_schema_extra)

    extra_data: dict[str, Any] | str | None = None

    @field_serializer('created_at', 'updated_at', 'last_sync_at', 'last_success_at', 'next_sync_at')
    def serialize_datetime(self, dt: datetime | None) -> str:
        return dt.strftime('%Y-%m-%d %H:%M:%S') if dt else ''

    @classmethod
    @model_validator(mode='before')
    def validate_extra_data(cls, data):
        if isinstance(data, dict) and 'extra_data' in data and isinstance(data['extra_data'], str):
            try:
                data['extra_data'] = json.loads(data['extra_data'])
            except json.JSONDecodeError:
                data['extra_data'] = {}
        return data

    total_extract: int = 0
    is_nsfw: bool
    is_special_followed: bool = False
    sync_status: str = 'idle'
    last_sync_at: datetime | None = None
    last_success_at: datetime | None = None
    next_sync_at: datetime | None = None
    last_error: str | None = None
    pending_video_count: int = 0
    site: str | None = None
