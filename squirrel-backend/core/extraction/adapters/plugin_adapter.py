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

from crawl import Video, Actor
from ..dto import VideoDTO, ActorDTO
from ..exceptions import DataTransformError

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
    
    def adapt(self, video: Video, site_name: str) -> VideoDTO:
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
    
    def _extract_base_fields(self, video: Video, site_name: str) -> Dict[str, Any]:
        """
        提取基础字段
        
        Args:
            video: Video对象
            site_name: 站点名称
            
        Returns:
            基础字段字典
        """
        # 只添加实际存在且不为None的字段
        base_data = {
            'url': video.url,
            'title': video.title or '',
            'site_name': site_name,
        }
        
        # 可选字段 - 只添加存在且有效的
        if hasattr(video, 'thumbnail'):
            thumbnail = video.thumbnail
            if thumbnail is not None and isinstance(thumbnail, str):
                base_data['thumbnail'] = thumbnail
        
        if hasattr(video, 'duration'):
            duration = video.duration
            if duration is not None and isinstance(duration, int):
                base_data['duration'] = duration
        
        if hasattr(video, 'description'):
            description = video.description
            if description is not None and isinstance(description, str):
                base_data['description'] = description
        
        if hasattr(video, 'tags'):
            tags = video.tags
            if tags is not None and isinstance(tags, list):
                base_data['tags'] = tags
        
        return base_data
    
    def _extract_publish_date(self, video: Video) -> Optional[datetime]:
        """
        提取发布时间（兼容多种格式）
        
        Args:
            video: Video对象
            
        Returns:
            datetime对象或None
        """
        # 优先使用publish_date
        if hasattr(video, 'publish_date'):
            publish_date = video.publish_date
            if publish_date is not None and isinstance(publish_date, datetime):
                return publish_date
        
        # 回退到upload_date
        if hasattr(video, 'upload_date'):
            upload_date = video.upload_date
            if upload_date is not None and isinstance(upload_date, datetime):
                return upload_date
        
        return None
    
    def _extract_actors(self, video: Video) -> List[ActorDTO]:
        """
        提取actors信息
        
        **关键改进：**
        - 主动调用video.actors属性
        - 可能触发HTTP请求（但在Adapter阶段，不在后端事务中）
        - 如果失败，记录警告但不中断流程
        
        Args:
            video: Video对象
            
        Returns:
            ActorDTO列表
        """
        actors = []
        
        try:
            # 访问actors属性（可能触发懒加载/HTTP请求）
            if hasattr(video, 'actors'):
                raw_actors = video.actors
                
                if raw_actors and isinstance(raw_actors, list):
                    for actor in raw_actors:
                        try:
                            actor_dto = self._convert_actor(actor)
                            if actor_dto:
                                actors.append(actor_dto)
                        except Exception as e:
                            self.logger.warning(
                                f"Failed to convert actor: {e}",
                                extra={
                                    'video_url': getattr(video, 'url', None),
                                    'actor_url': getattr(actor, 'url', None)
                                }
                            )
        
        except Exception as e:
            # actors获取失败不应该导致整个提取失败
            self.logger.warning(
                f"Failed to extract actors: {getattr(video, 'url', 'unknown')}, error: {e}",
                extra={
                    'url': getattr(video, 'url', None),
                    'error': str(e)
                }
            )
        
        return actors
    
    def _convert_actor(self, actor: Actor) -> Optional[ActorDTO]:
        """
        转换单个Actor对象为ActorDTO
        
        Args:
            actor: Actor对象
            
        Returns:
            ActorDTO或None
        """
        if not isinstance(actor, Actor):
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
    
    def _extract_raw_data(self, video: Video) -> Dict[str, Any]:
        """
        提取原始数据（用于调试和审计）
        
        Args:
            video: Video对象
            
        Returns:
            原始数据字典
        """
        raw = {}
        
        # 保存base_info（如果存在）
        if hasattr(video, '_base_info'):
            try:
                base_info = video._base_info
                if isinstance(base_info, dict):
                    # 只保存可序列化的数据
                    raw['base_info'] = {
                        k: v for k, v in base_info.items()
                        if isinstance(v, (str, int, float, bool, type(None)))
                    }
            except Exception as e:
                self.logger.debug(f"Failed to extract base_info: {e}")
        
        # 保存其他元数据
        if hasattr(video, 'DOMAIN'):
            raw['domain'] = video.DOMAIN
        
        return raw
