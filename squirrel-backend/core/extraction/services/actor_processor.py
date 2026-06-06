"""
演员处理服务 - 负责演员/UP主数据的处理
"""
import logging
from typing import List

from ..dto import ActorDTO
from services import creator_service, video_creator_service

logger = logging.getLogger(__name__)


class ActorProcessorService:
    """
    演员处理服务
    
    职责：
    - 创建或获取演员记录
    - 创建视频-演员关联
    """
    
    def process_actors(self, video_id: int, actors: List[ActorDTO]):
        """
        处理演员列表
        
        Args:
            video_id: 视频ID
            actors: 演员DTO列表
        """
        if not actors:
            return
        
        logger.debug(f"Processing {len(actors)} actors for video_id={video_id}")
        
        for actor_dto in actors:
            try:
                self._process_single_actor(video_id, actor_dto)
            except (ValueError, TypeError, AttributeError) as e:
                logger.warning(
                    f"Failed to process actor: video_id={video_id}, "
                    f"actor_url={actor_dto.url}, error={e}"
                )
                # 继续处理其他演员
    
    def _process_single_actor(self, video_id: int, actor_dto: ActorDTO):
        """处理单个演员"""
        # 1. 获取或创建演员
        creator = creator_service.get_creator_by_url(actor_dto.url)
        
        if not creator:
            creator = creator_service.create_creator(
                actor_dto.url,
                actor_dto.name,
                actor_dto.avatar
            )
            logger.debug(
                f"Created new creator: id={creator.id}, "
                f"name={actor_dto.name}"
            )
        
        # 2. 创建视频-演员关联
        video_creator = video_creator_service.get_video_creator(
            video_id, creator.id
        )
        
        if not video_creator:
            video_creator_service.create_video_creator(
                video_id, creator.id
            )
            logger.debug(
                f"Created video-creator link: "
                f"video_id={video_id}, creator_id={creator.id}"
            )


# 单例实例
actor_processor_service = ActorProcessorService()
