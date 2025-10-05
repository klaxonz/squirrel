"""
订阅更新策略基类
每个站点可以实现自己的更新策略
"""
from abc import ABC, abstractmethod
from typing import List, Optional
from ..models import SubscriptionUpdateRequest, SubscriptionUpdateResult, UpdateTrigger


class UpdateStrategy(ABC):
    """更新策略接口"""
    
    @property
    @abstractmethod
    def site_name(self) -> str:
        """站点名称（如 'youtube', 'bilibili'）"""
        pass
    
    @abstractmethod
    def should_update(self, request: SubscriptionUpdateRequest) -> tuple[bool, Optional[str]]:
        """
        判断是否需要更新
        
        Returns:
            (是否更新, 跳过原因)
        """
        pass
    
    @abstractmethod
    def fetch_videos(self, request: SubscriptionUpdateRequest) -> List[str]:
        """
        获取视频列表
        
        Returns:
            视频URL列表
        """
        pass
    
    @abstractmethod
    def enqueue_extraction(self, video_urls: List[str], request: SubscriptionUpdateRequest) -> int:
        """
        将视频加入提取队列
        
        Returns:
            成功入队的视频数量
        """
        pass
    
    def execute(self, request: SubscriptionUpdateRequest) -> SubscriptionUpdateResult:
        """
        执行更新流程（模板方法）
        """
        should_update, skip_reason = self.should_update(request)
        if not should_update:
            return SubscriptionUpdateResult(
                subscription_id=request.subscription_id,
                success=True,
                videos_found=0,
                videos_enqueued=0,
                skipped_reason=skip_reason
            )
        
        try:
            video_urls = self.fetch_videos(request)
            
            enqueued = self.enqueue_extraction(video_urls, request)
            
            # 在视频 URL 入队后，更新 offset
            self._update_offset_after_enqueue(request)
            
            return SubscriptionUpdateResult(
                subscription_id=request.subscription_id,
                success=True,
                videos_found=len(video_urls),
                videos_enqueued=enqueued
            )
        except Exception as e:
            return SubscriptionUpdateResult(
                subscription_id=request.subscription_id,
                success=False,
                videos_found=0,
                videos_enqueued=0,
                error_message=str(e)
            )
    
    def _update_offset_after_enqueue(self, request: SubscriptionUpdateRequest):
        """
        在视频入队后更新偏移量
        """
        try:
            # 只有定时任务触发的更新才需要记录 offset
            if request.trigger != UpdateTrigger.SCHEDULED:
                return
            
            # 从 request 中获取 domain（需要在消费者中解析并传入）
            domain = getattr(request, 'domain', None)
            if not domain:
                # 如果没有 domain，尝试从 URL 提取
                from utils import url_helper
                try:
                    domain = url_helper.extract_top_level_domain(request.url)
                except Exception:
                    domain = 'unknown'
            
            # 更新 offset
            from services.subscription_update.scheduler import SubscriptionScheduler
            SubscriptionScheduler.update_offset(domain, request.mode, request.subscription_id)
            
        except Exception as e:
            # offset 更新失败不应影响主流程
            import logging
            logger = logging.getLogger()
            logger.warning(f"Failed to update offset for subscription {request.subscription_id}: {e}")

