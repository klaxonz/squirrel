"""
插件数据适配器 - 将插件Video对象转换为VideoDTO

核心改进：
1. 主动获取所有需要的数据（包括懒加载的actors）
2. 捕获所有异常并标准化
3. 返回纯数据对象（VideoDTO）
"""
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime

from ..dto import VideoDTO, ActorDTO
from ..dto.validators import parse_publish_date
from ..exceptions import DataTransformError
from ..plugin_payloads import PluginActorData, PluginVideoData

logger = logging.getLogger(__name__)


class PluginDataAdapter:
    """
    插件数据适配器
    
    职责：
    - 将插件的Video对象转换为VideoDTO
    - 主动触发懒加载属性（如actors）
    - 统一数据格式
    - 错误处理和日志
    """
    
    def __init__(self):
        self.logger = logger
    
    def adapt(self, video: PluginVideoData, site_name: str) -> VideoDTO:
        """
        将插件的Video对象转换为VideoDTO
        
        Args:
            video: 插件返回的Video对象
            site_name: 站点名称
            
        Returns:
            VideoDTO对象
            
        Raises:
            DataTransformError: 转换失败
        """
        try:
            # 1. 提取基础字段
            base_data = self._extract_base_fields(video, site_name)
            
            # 2. 处理发布时间
            publish_date = self._extract_publish_date(video)
            if publish_date:
                base_data['publish_date'] = publish_date
            
            # 3. 主动获取actors（关键！）
            actors = self._extract_actors(video)
            if actors:
                base_data['actors'] = actors
            
            # 4. 保留原始数据
            base_data['raw_data'] = self._extract_raw_data(video)
            
            # 5. 创建DTO（自动验证）
            video_dto = VideoDTO(**base_data)
            
            self.logger.debug(
                f"Video adapted successfully: {video.url}",
                extra={
                    'url': video.url,
                    'site': site_name,
                    'actors_count': len(actors)
                }
            )
            
            return video_dto
        
        except Exception as e:
            self.logger.error(
                f"Failed to adapt Video to VideoDTO: {getattr(video, 'url', 'unknown')}",
                exc_info=True,
                extra={
                    'url': getattr(video, 'url', None),
                    'site': site_name,
                    'error': str(e),
                    'error_type': type(e).__name__
                }
            )
            
            raise DataTransformError(
                f"Failed to transform video data: {e}",
                context={
                    'url': getattr(video, 'url', None),
                    'site': site_name,
                    'original_error': str(e)
                }
            ) from e
    
    def _extract_base_fields(self, video: PluginVideoData, site_name: str) -> Dict[str, Any]:
        """
        提取基础字段
        
        Args:
            video: VideoMeta对象
            site_name: 站点名称
            
        Returns:
            基础字段字典
        """
        # VideoMeta 的基础字段
        base_data = {
            'url': video.url,
            'title': video.title or '',
            'site_name': site_name,
        }
        
        # 可选字段
        if video.thumbnail is not None:
            base_data['thumbnail'] = video.thumbnail
        
        if video.duration is not None:
            base_data['duration'] = video.duration
        
        # 从 extra_data 中提取额外字段（如 description, tags）
        if video.extra_data:
            if 'description' in video.extra_data:
                base_data['description'] = video.extra_data['description']
            if 'tags' in video.extra_data:
                base_data['tags'] = video.extra_data['tags']
        
        return base_data
    
    def _extract_publish_date(self, video: PluginVideoData) -> Optional[datetime]:
        """
        提取发布时间（兼容多种格式）
        
        Args:
            video: VideoMeta对象
            
        Returns:
            datetime对象或None
        """
        # VideoMeta 的 publish_date 字段
        if video.publish_date is not None:
            return parse_publish_date(video.publish_date)
        
        return None
    
    def _extract_actors(self, video: PluginVideoData) -> List[ActorDTO]:
        """
        提取actors信息
        
        VideoMeta 中 actors 可能在 extra_data 中
        
        Args:
            video: VideoMeta对象
            
        Returns:
            ActorDTO列表
        """
        actors = []
        
        try:
            # 从 extra_data 中获取 actors
            if video.extra_data and 'actors' in video.extra_data:
                raw_actors = video.extra_data['actors']
                
                if raw_actors and isinstance(raw_actors, list):
                    for actor in raw_actors:
                        try:
                            # Convert dictionary payloads to backend-local actor data.
                            if isinstance(actor, dict):
                                actor = PluginActorData(
                                    url=actor.get('url', ''),
                                    name=actor.get('name'),
                                    avatar=actor.get('avatar'),
                                    extra_data=actor.get('extra_data')
                                )
                            
                            actor_dto = self._convert_actor(actor)
                            if actor_dto:
                                actors.append(actor_dto)
                        except Exception as e:
                            self.logger.warning(
                                f"Failed to convert actor: {e}",
                                extra={
                                    'video_url': video.url,
                                    'actor': str(actor)
                                }
                            )
        
        except Exception as e:
            # actors获取失败不应该导致整个提取失败
            self.logger.warning(
                f"Failed to extract actors: {video.url}, error: {e}",
                extra={
                    'url': video.url,
                    'error': str(e)
                }
            )
        
        return actors
    
    def _convert_actor(self, actor: PluginActorData) -> Optional[ActorDTO]:
        """
        转换单个Actor对象为ActorDTO
        
        Args:
            actor: Actor对象
            
        Returns:
            ActorDTO或None
        """
        if not isinstance(actor, PluginActorData):
            return None
        
        # 确保有url和name
        if not hasattr(actor, 'url') or not actor.url:
            return None
        
        if not hasattr(actor, 'name') or not actor.name:
            return None
        
        return ActorDTO(
            url=actor.url,
            name=actor.name,
            avatar=getattr(actor, 'avatar', None)
        )
    
    def _extract_raw_data(self, video: PluginVideoData) -> Dict[str, Any]:
        """
        提取原始数据（用于调试和审计）
        
        Args:
            video: VideoMeta对象
            
        Returns:
            原始数据字典
        """
        raw = {}
        
        # 保存 extra_data（如果存在）
        if video.extra_data:
            # 只保存可序列化的数据
            raw['extra_data'] = {
                k: v for k, v in video.extra_data.items()
                if isinstance(v, (str, int, float, bool, type(None), list, dict))
            }
        
        return raw
