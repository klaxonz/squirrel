from __future__ import annotations

from datetime import datetime


def build_metric_key(
    name: str,
    tags: dict[str, str] | None,
    metric_type: str,
    window: str = '',
) -> str:
    parts = ['metrics', metric_type, name]
    if tags:
        parts.append(','.join(f'{key}={value}' for key, value in sorted(tags.items())))
    else:
        parts.append('_')

    if window:
        if window == 'total':
            parts.append('total')
        else:
            minute = datetime.now().strftime('%Y%m%d%H%M')
            parts.append(f'{window}:{minute}')

    return ':'.join(parts)


def parse_metric_key(key: str) -> tuple[str, str, dict[str, str]] | None:
    parts = key.split(':')
    if len(parts) < 4:
        return None

    metric_type = parts[1]
    metric_name = parts[2]
    labels = parse_tag_string(parts[3])
    return metric_type, metric_name, labels


def parse_tag_string(tags_str: str) -> dict[str, str]:
    if tags_str == '_':
        return {}

    labels = {}
    for tag in tags_str.split(','):
        if '=' in tag:
            key, value = tag.split('=', 1)
            labels[key] = value
    return labels
