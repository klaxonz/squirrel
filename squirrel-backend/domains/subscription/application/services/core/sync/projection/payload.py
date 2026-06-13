from __future__ import annotations

from datetime import datetime


def payload_int(payload: dict | None, key: str, default: int = 0) -> int:
    if not payload:
        return default
    value = payload.get(key, default)
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def payload_text(payload: dict | None, key: str, default: str | None = None) -> str | None:
    if not payload:
        return default
    value = payload.get(key)
    if value in (None, ''):
        return default
    return str(value)


def payload_datetime(payload: dict | None, key: str) -> datetime | None:
    if not payload or key not in payload:
        return None
    value = payload.get(key)
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        normalized = value.strip()
        if not normalized:
            return None
        try:
            return datetime.fromisoformat(normalized)
        except ValueError:
            try:
                return datetime.strptime(normalized, '%Y-%m-%d %H:%M:%S')
            except ValueError:
                return None
    return None
