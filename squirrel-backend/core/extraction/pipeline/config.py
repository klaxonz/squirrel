"""
Pipeline配置模块
"""
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Type, TYPE_CHECKING

if TYPE_CHECKING:
    from .base import PipelineStage


@dataclass
class StageConfig:
    """Stage配置"""
    stage_class: Type["PipelineStage"]
    enabled: bool = True
    critical: bool = True
    params: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PipelineConfig:
    """Pipeline配置"""
    stages: List[StageConfig] = field(default_factory=list)
    critical_stages: List[str] = field(default_factory=lambda: [
        "extraction",
        "validation",
        "persistence",
    ])

    def add_stage(
        self,
        stage_class: Type["PipelineStage"],
        enabled: bool = True,
        critical: bool = True,
        **params: Any
    ) -> "PipelineConfig":
        self.stages.append(StageConfig(
            stage_class=stage_class,
            enabled=enabled,
            critical=critical,
            params=params,
        ))
        return self

    def get_enabled_stages(self) -> List[StageConfig]:
        return [s for s in self.stages if s.enabled]

    @classmethod
    def default(cls) -> "PipelineConfig":
        from .stages import (
            ExtractionStage,
            ValidationStage,
            PersistenceStage,
            PostProcessStage,
        )
        config = cls()
        config.add_stage(ExtractionStage, critical=True)
        config.add_stage(ValidationStage, critical=True)
        config.add_stage(PersistenceStage, critical=True)
        config.add_stage(PostProcessStage, critical=False)
        return config
