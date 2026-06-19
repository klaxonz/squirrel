"""Pipeline context - passes data between Stages"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from ..contracts import ExtractionTask
from ..dto.video_dto import VideoDTO
from ..runtime_payloads import RuntimeVideoData


@dataclass
class PipelineContext:
    """Pipeline execution context

    Passes data and state between Pipeline Stages.
    Each Stage can read/write data in the context.
    """

    # ========== Input ==========
    task: ExtractionTask

    # ========== Intermediate data (filled by Stages) ==========
    plugin_video: RuntimeVideoData | None = None  # ExtractionStage fills this payload
    video_dto: VideoDTO | None = None  # Filled by ValidationStage
    video_model: Any | None = None  # Filled by PersistenceStage (VideoModel)

    # ========== Metadata ==========
    start_time: datetime = field(default_factory=datetime.now)
    current_stage: str = 'init'
    errors: list[str] = field(default_factory=list)

    # ========== Control flags ==========
    should_skip_persistence: bool = False  # Whether to skip persistence
    should_skip_post_process: bool = False  # Whether to skip post-processing

    # ========== Extra data ==========
    extra: dict[str, Any] = field(default_factory=dict)  # Store additional data

    def add_error(self, stage: str, error: str):
        """Add error message"""
        self.errors.append(f'[{stage}] {error}')

    def has_errors(self) -> bool:
        """Whether there are any errors"""
        return len(self.errors) > 0

    def get_duration(self) -> float:
        """Get execution duration in seconds"""
        return (datetime.now() - self.start_time).total_seconds()

    def __repr__(self):
        return (
            f'PipelineContext('
            f'task_id={self.task.task_id}, '
            f'stage={self.current_stage}, '
            f'duration={self.get_duration():.2f}s)'
        )
