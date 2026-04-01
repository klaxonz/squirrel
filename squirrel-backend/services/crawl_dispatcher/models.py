from dataclasses import dataclass, field


@dataclass
class DispatcherQuotaSnapshot:
    site_running: dict[str, int] = field(default_factory=dict)
    task_type_running: dict[str, int] = field(default_factory=dict)
