"""
Pipeline基类定义
"""
import logging
from abc import ABC, abstractmethod
from typing import List, Optional

from crawl import ExtractionResult
from .context import PipelineContext
from ..exceptions import PipelineError, StageExecutionError

logger = logging.getLogger(__name__)


class PipelineStage(ABC):
    """
    Pipeline阶段基类
    
    每个Stage负责Pipeline中的一个特定步骤。
    """
    
    @property
    @abstractmethod
    def stage_name(self) -> str:
        """阶段名称（用于日志和错误追踪）"""
        pass
    
    @abstractmethod
    def execute(self, context: PipelineContext) -> PipelineContext:
        """
        执行阶段逻辑
        
        Args:
            context: Pipeline上下文
            
        Returns:
            更新后的上下文
            
        Raises:
            StageExecutionError: 阶段执行失败
        """
        pass
    
    def can_skip(self, context: PipelineContext) -> bool:
        """
        判断是否可以跳过该阶段
        
        Args:
            context: Pipeline上下文
            
        Returns:
            True表示跳过，False表示执行
        """
        return False
    
    def on_error(self, context: PipelineContext, error: Exception) -> None:
        """
        错误处理回调
        
        Args:
            context: Pipeline上下文
            error: 捕获的异常
        """
        error_msg = f"Stage '{self.stage_name}' failed: {str(error)}"
        
        logger.error(
            error_msg,
            exc_info=True,
            extra={
                'task_id': context.task.task_id,
                'url': context.task.url,
                'stage': self.stage_name,
                'error_type': type(error).__name__
            }
        )
        
        context.add_error(self.stage_name, str(error))


class ExtractionPipeline:
    """
    提取Pipeline
    
    按顺序执行多个Stage，完成整个提取流程。
    """
    
    def __init__(self, stages: List[PipelineStage]):
        """
        初始化Pipeline
        
        Args:
            stages: Stage列表（按执行顺序）
        """
        self.stages = stages
        self.logger = logger
    
    def execute(self, context: PipelineContext) -> ExtractionResult:
        """
        执行Pipeline
        
        Args:
            context: Pipeline上下文
            
        Returns:
            ExtractionResult
        """
        try:
            self.logger.info(
                f"Pipeline started: task_id={context.task.task_id}, url={context.task.url}"
            )
            
            # 依次执行各个Stage
            for stage in self.stages:
                context.current_stage = stage.stage_name
                
                # 检查是否跳过
                if stage.can_skip(context):
                    self.logger.debug(
                        f"Skipping stage '{stage.stage_name}': task_id={context.task.task_id}"
                    )
                    continue
                
                # 执行Stage
                try:
                    self.logger.debug(
                        f"Executing stage '{stage.stage_name}': task_id={context.task.task_id}"
                    )
                    
                    context = stage.execute(context)
                    
                    self.logger.debug(
                        f"Stage '{stage.stage_name}' completed: task_id={context.task.task_id}"
                    )
                
                except Exception as e:
                    # Stage执行失败
                    stage.on_error(context, e)
                    
                    # 判断是否应该继续执行
                    if not self._should_continue_after_error(stage, e):
                        raise StageExecutionError(
                            f"Critical stage '{stage.stage_name}' failed",
                            stage_name=stage.stage_name,
                            context={
                                'task_id': context.task.task_id,
                                'url': context.task.url,
                                'error': str(e)
                            }
                        ) from e
            
            # 所有Stage执行完成
            duration = context.get_duration()
            
            self.logger.info(
                f"Pipeline completed successfully: task_id={context.task.task_id}, "
                f"duration={duration:.2f}s"
            )
            
            return ExtractionResult(
                success=True,
                data=context.video_dto
            )
        
        except Exception as e:
            duration = context.get_duration()
            
            self.logger.error(
                f"Pipeline failed: task_id={context.task.task_id}, "
                f"duration={duration:.2f}s, error={str(e)}",
                exc_info=True
            )
            
            return ExtractionResult(
                success=False,
                error=str(e)
            )
    
    def _should_continue_after_error(
        self,
        stage: PipelineStage,
        error: Exception
    ) -> bool:
        """
        判断Stage失败后是否应该继续执行
        
        Args:
            stage: 失败的Stage
            error: 捕获的异常
            
        Returns:
            True表示继续，False表示中断
        """
        # 定义关键Stage（失败必须中断）
        critical_stages = {
            'extraction',      # 提取失败，无法继续
            'validation',      # 验证失败，数据不完整
            'persistence',     # 持久化失败，无法保存
        }
        
        # 关键Stage失败，必须中断
        if stage.stage_name in critical_stages:
            return False
        
        # 非关键Stage失败，可以继续（如enrichment、post_process）
        return True
    
    def get_stage_names(self) -> List[str]:
        """获取所有Stage名称"""
        return [stage.stage_name for stage in self.stages]
    
    def __repr__(self):
        stage_names = ', '.join(self.get_stage_names())
        return f"ExtractionPipeline(stages=[{stage_names}])"
