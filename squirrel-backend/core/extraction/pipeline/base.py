"""Pipeline基类定义
"""
import logging
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Optional

from ..contracts import ExtractionResult
from ..exceptions import StageExecutionError
from .context import PipelineContext

if TYPE_CHECKING:
    from .middleware import MiddlewareChain

logger = logging.getLogger(__name__)


class PipelineStage(ABC):
    """Pipeline阶段基类

    每个Stage负责Pipeline中的一个特定步骤。
    """

    @property
    @abstractmethod
    def stage_name(self) -> str:
        """阶段名称（用于日志和错误追踪）"""

    @abstractmethod
    def execute(self, context: PipelineContext) -> PipelineContext:
        """执行阶段逻辑

        Args:
            context: Pipeline上下文

        Returns:
            更新后的上下文

        Raises:
            StageExecutionError: 阶段执行失败

        """

    def can_skip(self, context: PipelineContext) -> bool:
        """判断是否可以跳过该阶段

        Args:
            context: Pipeline上下文

        Returns:
            True表示跳过，False表示执行

        """
        return False

    def on_error(self, context: PipelineContext, error: Exception) -> None:
        """错误处理回调

        Args:
            context: Pipeline上下文
            error: 捕获的异常

        """
        error_msg = f"Stage '{self.stage_name}' failed: {error!s}"

        logger.error(
            error_msg,
            exc_info=True,
            extra={
                "task_id": context.task.task_id,
                "url": context.task.url,
                "stage": self.stage_name,
                "error_type": type(error).__name__,
            },
        )

        context.add_error(self.stage_name, str(error))


class ExtractionPipeline:
    """提取Pipeline

    按顺序执行多个Stage，完成整个提取流程。
    """

    def __init__(self, stages: list[PipelineStage], middleware: Optional["MiddlewareChain"] = None):
        """初始化Pipeline

        Args:
            stages: Stage列表（按执行顺序）
            middleware: 中间件链（可选）

        """
        self.stages = stages
        self._middleware = middleware
        self.logger = logger

    def execute(self, context: PipelineContext) -> ExtractionResult:
        """执行Pipeline

        Args:
            context: Pipeline上下文

        Returns:
            ExtractionResult

        """
        try:
            self.logger.info("Pipeline started: task_id=%s, url=%s", context.task.task_id, context.task.url)

            # 依次执行各个Stage
            for stage in self.stages:
                context.current_stage = stage.stage_name

                # 检查是否跳过
                if stage.can_skip(context):
                    self.logger.debug("Skipping stage '%s': task_id=%s", stage.stage_name, context.task.task_id)
                    continue

                # 执行Stage
                try:
                    self.logger.debug("Executing stage '%s': task_id=%s", stage.stage_name, context.task.task_id)

                    if self._middleware:
                        self._middleware.before_stage(context, stage)

                    context = stage.execute(context)

                    if self._middleware:
                        self._middleware.after_stage(context, stage)

                    self.logger.debug("Stage '%s' completed: task_id=%s", stage.stage_name, context.task.task_id)

                except (ValueError, TypeError, AttributeError, KeyError) as e:
                    # Stage执行失败
                    stage.on_error(context, e)
                    if self._middleware:
                        self._middleware.on_error(context, stage, e)

                    # 判断是否应该继续执行
                    if not self._should_continue_after_error(stage, e):
                        raise StageExecutionError(
                            f"Critical stage '{stage.stage_name}' failed",
                            stage_name=stage.stage_name,
                            context={
                                "task_id": context.task.task_id,
                                "url": context.task.url,
                                "error": str(e),
                            },
                        ) from e

            # 所有Stage执行完成
            duration = context.get_duration()

            self.logger.info("Pipeline completed successfully: task_id=%s, duration=%f'.2f's", context.task.task_id, duration)

            return ExtractionResult(
                success=True,
                data=context.video_dto,
            )

        except Exception as e:  # pipeline execution boundary — catch all to return ExtractionResult
            import traceback
            duration = context.get_duration()

            self.logger.error("Pipeline failed: task_id=%s, duration=%f'.2f's, error=%s", context.task.task_id, duration, e, exc_info=True)

            # 记录详细错误信息（包含堆栈）到 metrics
            try:
                from utils.metrics import metrics
                from utils.url_helper import extract_top_level_domain
                stack_trace = traceback.format_exc()
                site = extract_top_level_domain(context.task.url) if context.task.url else "unknown"
                metrics.record_error(
                    site=site,
                    url=context.task.url,
                    error_type=type(e).__name__,
                    error_msg=f"{e!s}\n\n{stack_trace}",
                )
            except Exception:  # metrics recording must never fail
                pass

            return ExtractionResult(
                success=False,
                error=str(e),
            )

    def _should_continue_after_error(
        self,
        stage: PipelineStage,
        error: Exception,
    ) -> bool:
        """判断Stage失败后是否应该继续执行

        Args:
            stage: 失败的Stage
            error: 捕获的异常

        Returns:
            True表示继续，False表示中断

        """
        # 定义关键Stage（失败必须中断）
        critical_stages = {
            "extraction",      # 提取失败，无法继续
            "validation",      # 验证失败，数据不完整
            "persistence",     # 持久化失败，无法保存
        }

        # 关键Stage失败，必须中断
        if stage.stage_name in critical_stages:
            return False

        # 非关键Stage失败，可以继续（如enrichment、post_process）
        return True

    def get_stage_names(self) -> list[str]:
        """获取所有Stage名称"""
        return [stage.stage_name for stage in self.stages]

    def __repr__(self):
        stage_names = ", ".join(self.get_stage_names())
        return f"ExtractionPipeline(stages=[{stage_names}])"
