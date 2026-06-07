from __future__ import annotations

from typing import Any

from .config import get_rate_limit_config


def _parse_bool(value: Any, default: bool = True) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    if isinstance(value, (int, float)):
        return bool(value)
    text = str(value).strip().lower()
    if text in {"true", "1", "yes", "y", "on"}:
        return True
    if text in {"false", "0", "no", "n", "off"}:
        return False
    return default


def _parse_float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def apply_ytdlp_rate_limit(site_slug: str, options: dict[str, Any] | None = None) -> dict[str, Any]:
    ydl_opts = dict(options or {})
    rate_limit = get_rate_limit_config(site_slug)
    if not rate_limit or not _parse_bool(rate_limit.get("enabled"), True):
        return ydl_opts

    min_interval = _parse_float(rate_limit.get("min_interval"))
    max_interval = _parse_float(rate_limit.get("max_interval"))
    if min_interval is None and max_interval is None:
        return ydl_opts

    if min_interval is None:
        min_interval = max_interval
    if max_interval is None:
        max_interval = min_interval
    if min_interval is None or max_interval is None:
        return ydl_opts

    min_interval = max(0.0, min_interval)
    max_interval = max(min_interval, max_interval)
    request_interval = min_interval if min_interval == max_interval else (min_interval + max_interval) / 2

    if request_interval > 0 and ydl_opts.get("sleep_interval_requests") in (None, ""):
        ydl_opts["sleep_interval_requests"] = request_interval

    if max_interval > 0:
        if ydl_opts.get("sleep_interval") in (None, ""):
            ydl_opts["sleep_interval"] = min_interval
        if ydl_opts.get("max_sleep_interval") in (None, ""):
            ydl_opts["max_sleep_interval"] = max_interval
        if ydl_opts.get("sleep_interval_subtitles") in (None, ""):
            ydl_opts["sleep_interval_subtitles"] = request_interval

    return ydl_opts
