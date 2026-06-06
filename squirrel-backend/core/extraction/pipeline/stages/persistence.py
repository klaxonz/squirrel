"""
PersistenceStage - 持久化视频数据到数据库
"""
import logging

from ..base import PipelineStage
from ..context import PipelineContext
from ...exceptions import DatabaseError

logger = logging.getLogger(__name__)


class PersistenceStage(PipelineStage):
    """
    持久化阶段
    
    职责：
    - 保存视频到数据库
    - 创建订阅-视频关联
    - 处理actors信息
    - 保存到context.video_model
    """
    
    def __init__(self, video_service, actor_service):
        """
        Args:
            video_service: 视频持久化服务
            actor_service: 演员处理服务
        """
        self.video_service = video_service
        self.actor_service = actor_service
    
    @property
    def stage_name(self) -> str:
        return "persistence"
    
    def execute(self, context: PipelineContext) -> PipelineContext:
        """执行持久化"""
        # 检查前置条件
        if context.video_dto is None:
            raise DatabaseError(
                "No video DTO found in context",
                context={'task_id': context.task.task_id}
            )
        
        # 检查是否跳过持久化
        if context.should_skip_persistence:
            logger.info(
                f"Skipping persistence (flag set): url={context.task.url}"
            )
            return context
        
        dto = context.video_dto
        task = context.task
        
        # 1. 保存视频
        logger.info(
            f"Persisting video: url={dto.url}, title={dto.title}"
        )
        
        try:
            video_model, is_new = self.video_service.create_or_update(
                url=dto.url,
                title=dto.title,
                thumbnail=dto.thumbnail,
                duration=dto.duration,
                publish_date=dto.publish_date,
                description=dto.description,
                subscription_id=task.metadata.get('subscription_id'),
                subscription_sync_mode=task.metadata.get('sync_mode'),
            )
            
            context.video_model = video_model
            context.extra['is_new_video'] = is_new
            
            logger.info(
                f"Video persisted: id={video_model.id}, "
                f"is_new={is_new}, url={dto.url}"
            )
        
        except Exception as e:
            raise DatabaseError(
                f"Failed to persist video: {e}",
                context={
                    'url': dto.url,
                    'title': dto.title
                }
            ) from e
        
        # 2. 处理actors
        if dto.has_actors():
            try:
                self.actor_service.process_actors(
                    video_model.id,
                    dto.actors
                )
                logger.info(
                    f"Actors processed: video_id={video_model.id}, "
                    f"count={len(dto.actors)}"
                )
            except Exception as e:
                # actors处理失败不应中断流程
                logger.warning(
                    f"Failed to process actors: video_id={video_model.id}, "
                    f"error={e}"
                )
        
        return context
    
    def can_skip(self, context: PipelineContext) -> bool:
        """如果已经有video_model或设置了跳过标志，可以跳过"""
        return (
            context.video_model is not None or
            context.should_skip_persistence
        )
