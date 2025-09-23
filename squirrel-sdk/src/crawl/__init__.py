"""Squirrel Crawl SDK

Light-weight SDK for building crawl / extraction plugins that can be loaded by
Squirrel backend and other Squirrel compatible runtimes.

Only pure-python stdlib dependencies are used to maximise portability.
"""

# `squirrel-sdk` is distributed as a **single wheel**; crawl is a sub-package.
# Keep version aligned with the root package instead of using a fictitious
# "squirrel-sdk-crawl" distribution.
from importlib.metadata import PackageNotFoundError, version as _pkg_version


def _detect_version() -> str:
    for dist_name in ("squirrel-sdk", "squirrel_sdk"):
        try:
            return _pkg_version(dist_name)  # type: ignore[arg-type]
        except PackageNotFoundError:
            continue
    # Development checkout – no installed distribution
    return "0.1.0.dev0"


__version__: str = _detect_version()

from .interfaces import (
    TaskStatus,
    ExtractionTask,
    ExtractionResult,
    VideoMeta,
    IExtractor,
    ITaskProcessor,
    IResultHandler,
    TaskPriority,
)
from .registry import (
    ExtractorRegistry,
    register_extractor,
    get_extractor_factory,
)
from .meta_origin import Video, Actor, SubscriptionMeta

__all__ = [
    "__version__",
    # interfaces
    "TaskStatus",
    "ExtractionTask",
    "ExtractionResult",
    "VideoMeta",
    "TaskPriority",
    "IExtractor",
    "ITaskProcessor",
    "IResultHandler",
    # base entities
    "Video",
    "Actor",
    "SubscriptionMeta",
    # registry helpers
    "ExtractorRegistry",
    "register_extractor",
    "get_extractor_factory",
    "BaseExtractor",
]

# Re-export for convenience
from .plugin_base import BaseExtractor  # noqa: E402  (import after __all__ definition)
