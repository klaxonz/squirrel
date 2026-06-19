"""Data validation utility functions"""

from datetime import datetime
from typing import Any


def validate_url(url: str) -> str:
    """Validate URL format

    Args:
        url: URL string

    Returns:
        Cleaned URL

    Raises:
        ValueError: Invalid URL format

    """
    if not url or not isinstance(url, str):
        raise ValueError('URL must be a non-empty string')

    url = url.strip()

    if not url:
        raise ValueError('URL cannot be empty or whitespace')

    if not url.startswith(('http://', 'https://')):
        raise ValueError('URL must start with http:// or https://')

    return url


def validate_not_empty(value: str, field_name: str = 'Field') -> str:
    """Validate string is not empty

    Args:
        value: Value to validate
        field_name: Field name (for error message)

    Returns:
        Cleaned string

    Raises:
        ValueError: Value is empty

    """
    if not value or not isinstance(value, str):
        raise ValueError(f'{field_name} must be a non-empty string')

    value = value.strip()

    if not value:
        raise ValueError(f'{field_name} cannot be empty or whitespace')

    return value


def parse_publish_date(value: Any) -> datetime | None:
    """Parse publish date (supports multiple formats)

    Supported formats:
    - datetime object
    - Unix timestamp (int/float)
    - String: YYYYMMDD, YYYY-MM-DD, YYYY/MM/DD, YYYY.MM.DD

    Args:
        value: Value to parse

    Returns:
        datetime object or None

    Raises:
        ValueError: Unparseable format

    """
    if value is None:
        return None

    # Already a datetime object
    if isinstance(value, datetime):
        return value

    # Unix timestamp
    if isinstance(value, (int, float)):
        try:
            return datetime.fromtimestamp(value)
        except (ValueError, OSError) as e:
            raise ValueError(f'Invalid timestamp: {value}') from e

    # String format
    if isinstance(value, str):
        value = value.strip()

        if not value:
            return None

        iso_value = value
        if iso_value.endswith('Z'):
            iso_value = f'{iso_value[:-1]}+00:00'

        try:
            return datetime.fromisoformat(iso_value)
        except ValueError:
            pass

        # Try multiple date formats
        date_formats = [
            '%Y%m%d',  # 20231207
            '%Y-%m-%d',  # 2023-12-07
            '%Y/%m/%d',  # 2023/12/07
            '%Y.%m.%d',  # 2023.12.07
            '%Y-%m-%d %H:%M:%S',  # 2023-12-07 15:30:45
            '%Y/%m/%d %H:%M:%S',  # 2023/12/07 15:30:45
        ]

        for fmt in date_formats:
            try:
                return datetime.strptime(value, fmt)
            except ValueError:
                continue

        # All formats failed
        raise ValueError(
            f'Cannot parse publish_date: {value}. Supported formats: YYYYMMDD, YYYY-MM-DD, YYYY/MM/DD, etc.',
        )

    raise ValueError(f'Unsupported publish_date type: {type(value)}')


def validate_duration(duration: int | None) -> int | None:
    """Validate video duration

    Args:
        duration: Duration in seconds

    Returns:
        Validated duration

    Raises:
        ValueError: Invalid duration

    """
    if duration is None:
        return None

    if not isinstance(duration, int):
        raise ValueError(f'Duration must be an integer, got {type(duration)}')

    if duration < 0:
        raise ValueError(f'Duration must be non-negative, got {duration}')

    return duration
