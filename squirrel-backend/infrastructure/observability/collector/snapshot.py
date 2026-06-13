from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass
class MetricSnapshot:
    """Metric snapshot data class."""

    metric_name: str
    metric_type: str
    labels: dict[str, str]
    value: float
    timestamp: datetime

    def to_dict(self) -> dict[str, Any]:
        """Convert to dict for JSON serialization."""
        return {
            'metric_name': self.metric_name,
            'metric_type': self.metric_type,
            'labels': self.labels,
            'value': self.value,
            'timestamp': self.timestamp.isoformat(),
        }
