"""数据验证工具函数
"""
from datetime import datetime
from typing import Any


def validate_url(url: str) -> str:
    """验证URL格式

    Args:
        url: URL字符串

    Returns:
        清理后的URL

    Raises:
        ValueError: URL格式无效

    """
    if not url or not isinstance(url, str):
        raise ValueError("URL must be a non-empty string")

    url = url.strip()

    if not url:
        raise ValueError("URL cannot be empty or whitespace")

    if not url.startswith(("http://", "https://")):
        raise ValueError("URL must start with http:// or https://")

    return url


def validate_not_empty(value: str, field_name: str = "Field") -> str:
    """验证字符串非空

    Args:
        value: 待验证的值
        field_name: 字段名称（用于错误消息）

    Returns:
        清理后的字符串

    Raises:
        ValueError: 值为空

    """
    if not value or not isinstance(value, str):
        raise ValueError(f"{field_name} must be a non-empty string")

    value = value.strip()

    if not value:
        raise ValueError(f"{field_name} cannot be empty or whitespace")

    return value


def parse_publish_date(value: Any) -> datetime | None:
    """解析发布时间（支持多种格式）

    支持的格式：
    - datetime对象
    - Unix timestamp（int/float）
    - 字符串: YYYYMMDD, YYYY-MM-DD, YYYY/MM/DD, YYYY.MM.DD

    Args:
        value: 待解析的值

    Returns:
        datetime对象或None

    Raises:
        ValueError: 无法解析的格式

    """
    if value is None:
        return None

    # 已经是datetime对象
    if isinstance(value, datetime):
        return value

    # Unix timestamp
    if isinstance(value, (int, float)):
        try:
            return datetime.fromtimestamp(value)
        except (ValueError, OSError) as e:
            raise ValueError(f"Invalid timestamp: {value}") from e

    # 字符串格式
    if isinstance(value, str):
        value = value.strip()

        if not value:
            return None

        iso_value = value
        if iso_value.endswith("Z"):
            iso_value = f"{iso_value[:-1]}+00:00"

        try:
            return datetime.fromisoformat(iso_value)
        except ValueError:
            pass

        # 尝试多种日期格式
        date_formats = [
            "%Y%m%d",           # 20231207
            "%Y-%m-%d",         # 2023-12-07
            "%Y/%m/%d",         # 2023/12/07
            "%Y.%m.%d",         # 2023.12.07
            "%Y-%m-%d %H:%M:%S",  # 2023-12-07 15:30:45
            "%Y/%m/%d %H:%M:%S",  # 2023/12/07 15:30:45
        ]

        for fmt in date_formats:
            try:
                return datetime.strptime(value, fmt)
            except ValueError:
                continue

        # 所有格式都失败
        raise ValueError(
            f"Cannot parse publish_date: {value}. "
            f"Supported formats: YYYYMMDD, YYYY-MM-DD, YYYY/MM/DD, etc.",
        )

    raise ValueError(f"Unsupported publish_date type: {type(value)}")


def validate_duration(duration: int | None) -> int | None:
    """验证视频时长

    Args:
        duration: 时长（秒）

    Returns:
        验证后的时长

    Raises:
        ValueError: 时长无效

    """
    if duration is None:
        return None

    if not isinstance(duration, int):
        raise ValueError(f"Duration must be an integer, got {type(duration)}")

    if duration < 0:
        raise ValueError(f"Duration must be non-negative, got {duration}")

    return duration
