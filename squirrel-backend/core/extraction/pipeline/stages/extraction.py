"""
ExtractionStage - 从插件提取视频数据
"""
import logging
from typing import Optional

from crawl import Extractor
from ..base import PipelineStage
from ..context import PipelineContext
from ...exceptions import (
    ExtractionError,
    NetworkError,
    PermissionError,
    ResourceNotFoundError,
    VipError,
)

logger = logging.getLogger(__name__)


class ExtractionStage(PipelineStage):
    """
    提取阶段

    职责：
    - 根据URL获取对应的提取器
    - 调用插件提取视频数据
    - 将结果保存到context.plugin_video
    """

    def __init__(self, extractor_factory):
        """
        Args:
            extractor_factory: 提取器工厂（ExtractorFactory实例）
        """
        self.extractor_factory = extractor_factory

    @property
    def stage_name(self) -> str:
        return "extraction"

    def execute(self, context: PipelineContext) -> PipelineContext:
        """执行提取"""
        extractor = self._get_extractor(context.task.url)

        if extractor is None:
            raise ExtractionError(
                f"No extractor found for URL: {context.task.url}",
                context={'url': context.task.url}
            )

        logger.info(
            f"Extracting video: url={context.task.url}, "
            f"site={context.task.site_name}"
        )

        result = extractor.extract(context.task)

        if not result.success:
            error_context = {
                'url': context.task.url,
                'site': context.task.site_name,
                'error_category': result.error_category,
                'retryable': result.retryable,
                **(result.error_context or {})
            }

            error_msg = result.error or "Extraction failed"

            if result.error_category == 'network':
                raise NetworkError(error_msg, context=error_context)
            elif result.error_category == 'auth':
                raise PermissionError(error_msg, context=error_context)
            elif result.error_category == 'vip':
                raise VipError(error_msg, context=error_context)
            elif result.error_category == 'not_found':
                raise ResourceNotFoundError(error_msg, context=error_context)
            else:
                raise ExtractionError(
                    error_msg,
                    retryable=result.retryable,
                    context=error_context
                )

        context.plugin_video = result.data

        logger.info(
            f"Extraction completed: url={context.task.url}, "
            f"title={getattr(result.data, 'title', 'N/A')}"
        )

        return context

    def on_error(self, context: PipelineContext, error: Exception) -> None:
        """错误处理回调"""
        # 调用父类的错误处理
        super().on_error(context, error)

        # 如果是VIP权限错误，记录到VIP视频表
        if isinstance(error, VipError):
            try:
                from services.vip_video_service import record_vip_video
                record_vip_video(
                    url=context.task.url,
                    error_message=str(error),
                    error_type=type(error).__name__
                )
            except Exception as record_error:
                logger.warning(
                    f"Failed to record VIP video: {record_error}"
                )

    def _get_extractor(self, url: str) -> Optional[Extractor]:
        """获取提取器"""
        try:
            return self.extractor_factory.create_extractor(url)
        except Exception as e:
            logger.error(f"Failed to create extractor: {e}")
            return None
