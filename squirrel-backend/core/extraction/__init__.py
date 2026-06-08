"""Core extraction module

Refactored data scraping framework providing a unified interface and extensible architecture.

Main components:
- interfaces: Core interface definitions
- base: Base implementation classes
- factory: Extractor factory
- task_manager: Task manager
- cache: Cache manager
- extractors: Site-specific extractor implementations
- handlers: Result handlers
"""


from .base import BaseExtractor, BaseResultHandler, BaseTaskProcessor
from .contracts import (
    ExtractionResult,
    ExtractionTask,
    Extractor,
    ResultHandler,
    TaskPriority,
    TaskProcessor,
    TaskStatus,
)
from .factory import (
    ExtractorFactory,
    get_extractor_factory,
    reset_factory,
)
from .runtime_payloads import RuntimeActorData, RuntimeVideoData
from .task_manager import TaskManager


# Lazy imports to avoid circular dependency with services.extraction
def _video_extraction_handler():
    from .handlers.video_handler import VideoExtractionHandler
    return VideoExtractionHandler


def __getattr__(name):
    if name == "VideoExtractionHandler":
        return _video_extraction_handler()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = [
    "TaskStatus",
    "TaskPriority",
    "ExtractionTask",
    "ExtractionResult",
    "Extractor",
    "TaskProcessor",
    "ResultHandler",
    "RuntimeVideoData",
    "RuntimeActorData",
    # Base classes
    "BaseExtractor", "BaseTaskProcessor", "BaseResultHandler",

    # Factory and registration
    "ExtractorFactory",
    "get_extractor_factory",
    "reset_factory",

    # Task management
    "TaskManager",

    # Handlers
    "VideoExtractionHandler",
]
