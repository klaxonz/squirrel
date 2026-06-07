"""Pipeline中间件机制
"""
import logging
import time
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .base import PipelineStage
    from .context import PipelineContext

logger = logging.getLogger(__name__)


class PipelineMiddleware(ABC):
    """Pipeline中间件基类"""

    @abstractmethod
    def before_stage(self, context: "PipelineContext", stage: "PipelineStage") -> None:
        """Stage执行前调用"""

    @abstractmethod
    def after_stage(self, context: "PipelineContext", stage: "PipelineStage") -> None:
        """Stage执行后调用"""

    def on_error(self, context: "PipelineContext", stage: "PipelineStage", error: Exception) -> None:
        """Stage执行出错时调用"""


class LoggingMiddleware(PipelineMiddleware):
    """日志中间件"""

    def before_stage(self, context: "PipelineContext", stage: "PipelineStage") -> None:
        logger.debug("[middleware] Starting stage: %s", stage.stage_name)

    def after_stage(self, context: "PipelineContext", stage: "PipelineStage") -> None:
        logger.debug("[middleware] Completed stage: %s", stage.stage_name)

    def on_error(self, context: "PipelineContext", stage: "PipelineStage", error: Exception) -> None:
        logger.error("[middleware] Stage %s failed: %s", stage.stage_name, error)


class TimingMiddleware(PipelineMiddleware):
    """计时中间件"""

    def __init__(self):
        self._start_times: dict = {}

    def before_stage(self, context: "PipelineContext", stage: "PipelineStage") -> None:
        self._start_times[stage.stage_name] = time.time()

    def after_stage(self, context: "PipelineContext", stage: "PipelineStage") -> None:
        start = self._start_times.pop(stage.stage_name, None)
        if start:
            duration = time.time() - start
            logger.info("[timing] Stage %s took %f'.3f's", stage.stage_name, duration)

    def on_error(self, context: "PipelineContext", stage: "PipelineStage", error: Exception) -> None:
        self._start_times.pop(stage.stage_name, None)


class MiddlewareChain:
    """中间件链"""

    def __init__(self, middlewares: list[PipelineMiddleware] = None):
        self._middlewares = middlewares or []

    def add(self, middleware: PipelineMiddleware) -> "MiddlewareChain":
        self._middlewares.append(middleware)
        return self

    def before_stage(self, context: "PipelineContext", stage: "PipelineStage") -> None:
        for mw in self._middlewares:
            try:
                mw.before_stage(context, stage)
            except Exception as e:  # middleware must not propagate
                logger.warning("[middleware] before_stage error: %s", e)

    def after_stage(self, context: "PipelineContext", stage: "PipelineStage") -> None:
        for mw in reversed(self._middlewares):
            try:
                mw.after_stage(context, stage)
            except Exception as e:  # middleware must not propagate
                logger.warning("[middleware] after_stage error: %s", e)

    def on_error(self, context: "PipelineContext", stage: "PipelineStage", error: Exception) -> None:
        for mw in reversed(self._middlewares):
            try:
                mw.on_error(context, stage, error)
            except Exception as e:  # middleware must not propagate
                logger.warning("[middleware] on_error error: %s", e)
