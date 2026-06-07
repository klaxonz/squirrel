"""演员处理服务 - 负责演员/UP主数据的处理
"""
import logging

from services import creator_service, video_creator_service

from ..dto import ActorDTO

logger = logging.getLogger(__name__)


class ActorProcessorService:
    """演员处理服务

    职责：
    - 创建或获取演员记录
    - 创建视频-演员关联
    """

    def process_actors(self, video_id: int, actors: list[ActorDTO]):
        """处理演员列表

        Args:
            video_id: 视频ID
            actors: 演员DTO列表

        """
        if not actors:
            return

        logger.debug("Processing %s actors for video_id=%s", len(actors), video_id)

        for actor_dto in actors:
            try:
                self._process_single_actor(video_id, actor_dto)
            except (ValueError, TypeError, AttributeError) as e:
                logger.warning("Failed to process actor: video_id=%s, actor_url=%s, error=%s", video_id, actor_dto.url, e)
                # 继续处理其他演员

    def _process_single_actor(self, video_id: int, actor_dto: ActorDTO):
        """处理单个演员"""
        # 1. 获取或创建演员
        creator = creator_service.get_creator_by_url(actor_dto.url)

        if not creator:
            creator = creator_service.create_creator(
                actor_dto.url,
                actor_dto.name,
                actor_dto.avatar,
            )
            logger.debug("Created new creator: id=%s, name=%s", creator.id, actor_dto.name)

        # 2. 创建视频-演员关联
        video_creator = video_creator_service.get_video_creator(
            video_id, creator.id,
        )

        if not video_creator:
            video_creator_service.create_video_creator(
                video_id, creator.id,
            )
            logger.debug("Created video-creator link: video_id=%s, creator_id=%s", video_id, creator.id)


# 单例实例
actor_processor_service = ActorProcessorService()
