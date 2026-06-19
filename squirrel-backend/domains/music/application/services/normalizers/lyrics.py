from __future__ import annotations

from typing import Any


def parse_lrc(content: str) -> list[dict[str, Any]]:
    lines = []
    for raw_line in content.splitlines():
        if not raw_line.startswith('[') or ']' not in raw_line:
            continue
        text = raw_line[raw_line.rfind(']') + 1 :].strip()
        for timestamp in raw_line[: raw_line.rfind(']') + 1].split(']'):
            if not timestamp.startswith('['):
                continue
            seconds = parse_lrc_timestamp(timestamp[1:])
            if seconds >= 0:
                lines.append({'time': seconds, 'text': text})
    return sorted(lines, key=lambda item: item['time'])


def parse_lrc_timestamp(value: str) -> float:
    if ':' not in value:
        return -1
    minutes_text, seconds_text = value.split(':', 1)
    try:
        return int(minutes_text) * 60 + float(seconds_text)
    except ValueError:
        return -1
