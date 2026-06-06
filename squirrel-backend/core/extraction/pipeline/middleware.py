"""
Pipeline中间件机制
"""
import logging
import time
from abc import ABC, abstractmethod
from typing import List, TYPE_CHECKING

if TYPE_CHECKING:
    from .context import PipelineContext
    from .base import PipelineStage

logger = logging.getLogger(__name__)


class PipelineMiddleware(ABC):
    """Pipeline中间件基类"""

    @abstractmethod
    def before_stage(self, context: "PipelineContext", stage: "PipelineStage") -> None:
        """Stage执行前调用"""
        pass

    @abstractmethod
    def after_stage(self, context: "PipelineContext", stage: "PipelineStage") -> None:
        """Stage执行后调用"""
        pass

    def on_error(self, context: "PipelineContext", stage: "PipelineStage", error: Exception) -> None:
        """Stage执行出错时调用"""
        pass


class LoggingMiddleware(PipelineMiddleware):
    """日志中间件"""

    def before_stage(self, context: "PipelineContext", stage: "PipelineStage") -> None:
        logger.debug(f"[middleware] Starting stage: {stage.stage_name}")

    def after_stage(self, context: "PipelineContext", stage: "PipelineStage") -> None:
        logger.debug(f"[middleware] Completed stage: {stage.stage_name}")

    def on_error(self, context: "PipelineContext", stage: "PipelineStage", error: Exception) -> None:
        logger.error(f"[middleware] Stage {stage.stage_name} failed: {error}")


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
            logger.info(f"[timing] Stage {stage.stage_name} took {duration:.3f}s")

    def on_error(self, context: "PipelineContext", stage: "PipelineStage", error: Exception) -> None:
        self._start_times.pop(stage.stage_name, None)


class MiddlewareChain:
    """中间件链"""

    def __init__(self, middlewares: List[PipelineMiddleware] = None):
        self._middlewares = middlewares or []

    def add(self, middleware: PipelineMiddleware) -> "MiddlewareChain":
        self._middlewares.append(middleware)
        return self

    def before_stage(self, context: "PipelineContext", stage: "PipelineStage") -> None:
        for mw in self._middlewares:
            try:
                mw.before_stage(context, stage)
            except Exception as e:  # middleware must not propagate
                logger.warning(f"[middleware] before_stage error: {e}")

    def after_stage(self, context: "PipelineContext", stage: "PipelineStage") -> None:
        for mw in reversed(self._middlewares):
            try:
                mw.after_stage(context, stage)
            except Exception as e:  # middleware must not propagate
                logger.warning(f"[middleware] after_stage error: {e}")

    def on_error(self, context: "PipelineContext", stage: "PipelineStage", error: Exception) -> None:
        for mw in reversed(self._middlewares):
            try:
                mw.on_error(context, stage, error)
            except Exception as e:  # middleware must not propagate
                logger.warning(f"[middleware] on_error error: {e}")
