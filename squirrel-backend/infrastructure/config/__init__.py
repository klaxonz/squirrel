"""Configuration package — public API.

Settings classes and helpers are re-exported here for convenience. The
``settings`` singleton is intentionally NOT re-exported: because this package
contains a ``settings`` submodule, ``from infrastructure.config import settings``
resolves to the submodule (Python gives submodules precedence over package
``__getattr__``), not the lazy instance. Use the fully-qualified
``from infrastructure.config.settings import settings`` instead — that path is
itself lazily resolved via PEP 562 on the submodule.
"""
from infrastructure.config.settings import (
    CookieCloudSettings,
    CrawlSettings,
    KugouMusicSettings,
    MeiliSettings,
    MqSettings,
    PostgresSettings,
    RedisSettings,
    Settings,
    get_settings,
)
from infrastructure.config.startup_dependencies import (
    StartupDependencyIssue,
    StartupIssues,
)

__all__ = [
    "CookieCloudSettings",
    "CrawlSettings",
    "KugouMusicSettings",
    "MeiliSettings",
    "MqSettings",
    "PostgresSettings",
    "RedisSettings",
    "Settings",
    "StartupDependencyIssue",
    "StartupIssues",
    "get_settings",
]
