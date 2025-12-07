"""
PostProcessStage - 后处理（缩略图、下载任务等）
"""
import logging

from ..base import PipelineStage
from ..context import PipelineContext

logger = logging.getLogger(__name__)


class PostProcessStage(PipelineStage):
    """
    后处理阶段
    
    职责：
    - 异步下载缩略图
    - 创建下载任务
    - 其他后处理操作
    """
    
    def __init__(self, thumbnail_service, task_service):
        """
        Args:
            thumbnail_service: 缩略图下载服务
            task_service: 下载任务服务
        """
        self.thumbnail_service = thumbnail_service
        self.task_service = task_service
    
    @property
    def stage_name(self) -> str:
        return "post_process"
    
    def execute(self, context: PipelineContext) -> PipelineContext:
        """执行后处理"""
        # 检查是否跳过
        if context.should_skip_post_process:
            logger.info(
                f"Skipping post-process (flag set): url={context.task.url}"
            )
            return context
        
        video_model = context.video_model
        video_dto = context.video_dto
        task = context.task
        
        # 检查前置条件
        if video_model is None or video_dto is None:
            logger.warning(
                f"Missing video_model or video_dto, skipping post-process: "
                f"url={context.task.url}"
            )
            return context
        
        # 1. 异步下载缩略图
        if video_dto.has_thumbnail():
            try:
                self.thumbnail_service.enqueue_download(
                    video_model.id,
                    video_dto.thumbnail,
                    video_dto.site_name
                )
                logger.info(
                    f"Thumbnail download enqueued: video_id={video_model.id}"
                )
            except Exception as e:
                # 缩略图下载失败不应中断流程
                logger.warning(
                    f"Failed to enqueue thumbnail download: "
                    f"video_id={video_model.id}, error={e}"
                )
        
        # 2. 创建下载任务
        only_extract = task.metadata.get('only_extract', True)
        if not only_extract:
            try:
                self.task_service.create_download_task(video_model)
                logger.info(
                    f"Download task created: video_id={video_model.id}"
                )
            except Exception as e:
                # 任务创建失败不应中断流程
                logger.warning(
                    f"Failed to create download task: "
                    f"video_id={video_model.id}, error={e}"
                )
        
        return context
    
    def can_skip(self, context: PipelineContext) -> bool:
        """如果设置了跳过标志，可以跳过"""
        return context.should_skip_post_process
