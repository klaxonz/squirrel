"""Pipeline配置模块
"""
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .base import PipelineStage


@dataclass
class StageConfig:
    """Stage配置"""

    stage_class: type["PipelineStage"]
    enabled: bool = True
    critical: bool = True
    params: dict[str, Any] = field(default_factory=dict)


@dataclass
class PipelineConfig:
    """Pipeline配置"""

    stages: list[StageConfig] = field(default_factory=list)
    critical_stages: list[str] = field(default_factory=lambda: [
        "extraction",
        "validation",
        "persistence",
    ])

    def add_stage(
        self,
        stage_class: type["PipelineStage"],
        enabled: bool = True,
        critical: bool = True,
        **params: Any,
    ) -> "PipelineConfig":
        self.stages.append(StageConfig(
            stage_class=stage_class,
            enabled=enabled,
            critical=critical,
            params=params,
        ))
        return self

    def get_enabled_stages(self) -> list[StageConfig]:
        return [s for s in self.stages if s.enabled]

    @classmethod
    def default(cls) -> "PipelineConfig":
        from .stages import (
            ExtractionStage,
            PersistenceStage,
            PostProcessStage,
            ValidationStage,
        )
        config = cls()
        config.add_stage(ExtractionStage, critical=True)
        config.add_stage(ValidationStage, critical=True)
        config.add_stage(PersistenceStage, critical=True)
        config.add_stage(PostProcessStage, critical=False)
        return config
