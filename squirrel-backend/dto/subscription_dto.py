import json
from datetime import datetime
from typing import Optional, Dict, Any, Union

from pydantic import model_validator, field_serializer
from sqlalchemy_to_pydantic import sqlalchemy_to_pydantic
from models.subscription import Subscription


class SubscriptionDto(sqlalchemy_to_pydantic(Subscription)):
    extra_data: Optional[Union[Dict[str, Any], str]] = None

    class Config:
        from_attributes = True
        json_encoders = {datetime: lambda v: v.strftime("%Y-%m-%d %H:%M:%S")}

        @staticmethod
        def json_schema_extra(schema: Dict[str, Any]) -> None:
            if 'properties' in schema and 'extra_data' in schema['properties']:
                schema['properties']['extra_data']['type'] = ['object', 'string', 'null']

    @field_serializer('created_at', 'updated_at')
    def serialize_datetime(self, dt: Optional[datetime]) -> str:
        return dt.strftime("%Y-%m-%d %H:%M:%S") if dt else ""

    @classmethod
    @model_validator(mode='before')
    def validate_extra_data(cls, data):
        if isinstance(data, dict) and 'extra_data' in data:
            if isinstance(data['extra_data'], str):
                try:
                    data['extra_data'] = json.loads(data['extra_data'])
                except json.JSONDecodeError:
                    data['extra_data'] = {}
        return data

    total_extract: int = 0
