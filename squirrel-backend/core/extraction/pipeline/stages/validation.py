"""ValidationStage - 验证并转换数据为DTO
"""
import logging

from ...adapters import RuntimeDataAdapter
from ...exceptions import ValidationError as ExtValidationError
from ..base import PipelineStage
from ..context import PipelineContext

logger = logging.getLogger(__name__)


class ValidationStage(PipelineStage):
    """验证阶段

    职责：
    - 将插件Video对象转换为VideoDTO
    - 验证数据完整性和格式
    - 保存到context.video_dto
    """

    def __init__(self, adapter: RuntimeDataAdapter):
        """Args:
        adapter: 插件数据适配器

        """
        self.adapter = adapter

    @property
    def stage_name(self) -> str:
        return "validation"

    def execute(self, context: PipelineContext) -> PipelineContext:
        """执行验证和转换"""
        # 检查前置条件
        if context.plugin_video is None:
            raise ExtValidationError(
                "No plugin video data found in context",
                context={"task_id": context.task.task_id},
            )

        # 转换为DTO（会自动验证）
        logger.info("Validating video data: url=%s", context.task.url)

        video_dto = self.adapter.adapt(
            context.plugin_video,
            context.task.site_name,
        )

        # 保存到上下文
        context.video_dto = video_dto

        logger.info("Validation completed: url=%s, title=%s, actors=%s", context.task.url, video_dto.title, len(video_dto.actors))

        return context

    def can_skip(self, context: PipelineContext) -> bool:
        """如果已经有video_dto，可以跳过"""
        return context.video_dto is not None
