"""Shared Pydantic serialization helpers for response schemas.

These keep response schemas DRY: every domain response schema that needs to
mirror the historical ``SerializerMixin`` datetime format
(``YYYY-MM-DD HH:MM:SS``, no timezone) uses :func:`serialize_datetime`.
"""

from datetime import datetime, date
from decimal import Decimal

from pydantic import field_serializer


def serialize_datetime(dt: datetime | None) -> str | None:
    """Format a datetime the way ``SerializerMixin._serialize_value`` did.

    Preserves the historical client-facing format (local-style, no timezone)
    so swapping ``to_dict()`` for Pydantic schemas does not change wire shape.
    """
    if dt is None:
        return None
    return dt.strftime('%Y-%m-%d %H:%M:%S')


def serialize_date(d: date | None) -> str | None:
    if d is None:
        return None
    return d.strftime('%Y-%m-%d')


def serialize_decimal(value: Decimal | None) -> str | None:
    if value is None:
        return None
    return str(value)


def datetime_serializer(*fields: str):
    """Build a ``@field_serializer(*fields)`` decorator bound to serialize_datetime.

    Usage in a BaseModel::

        created_at: datetime | None = None
        updated_at: datetime | None = None
        _ser = field_serializer('created_at', 'updated_at')(serialize_datetime)
    """
    return field_serializer(*fields)(serialize_datetime)
