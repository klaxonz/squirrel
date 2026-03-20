"""
订阅更新策略基类
每个站点可以实现自己的更新策略
"""
from abc import ABC, abstractmethod
from typing import Optional

from services import subscription_sync_state_service
from utils.metrics import metrics
from ..models import SubscriptionUpdateRequest, SubscriptionUpdateResult


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
    def fetch_videos(self, request: SubscriptionUpdateRequest):
        """
        获取视频列表
        """
        pass
    
    @abstractmethod
    def enqueue_extraction(self, fetch_result, request: SubscriptionUpdateRequest) -> int:
        """
        将视频加入提取队列
        """
        pass
    
    def execute(self, request: SubscriptionUpdateRequest) -> SubscriptionUpdateResult:
        """
        执行更新流程（模板方法）
        """
        # 获取站点信息用于指标标签
        from utils import url_helper
        try:
            domain = url_helper.extract_top_level_domain(request.url)
        except Exception:
            domain = "unknown"
        tags = {"site": domain}
        
        should_update, skip_reason = self.should_update(request)
        if not should_update:
            if request.sync_state_id:
                subscription_sync_state_service.mark_sync_skipped(request.sync_state_id)
            # 记录跳过指标
            metrics.counter("subscription.update.total", tags={**tags, "status": "skipped", "reason": skip_reason or "unknown"})
            return SubscriptionUpdateResult(
                subscription_id=request.subscription_id,
                success=True,
                videos_found=0,
                videos_enqueued=0,
                skipped_reason=skip_reason
            )
        
        try:
            fetch_result = self.fetch_videos(request)
            
            enqueued = self.enqueue_extraction(fetch_result, request)

            if request.sync_state_id:
                subscription_sync_state_service.mark_sync_success(
                    request.sync_state_id,
                    cursor_payload=fetch_result.cursor_payload,
                    latest_video_url=fetch_result.latest_video_url,
                    videos_found=len(fetch_result.video_urls),
                )
            
            # 记录成功指标
            metrics.counter("subscription.update.total", tags={**tags, "status": "success"})
            metrics.counter("subscription.videos.found", value=len(fetch_result.video_urls), tags=tags)
            metrics.counter("subscription.videos.enqueued", value=enqueued, tags=tags)
            
            return SubscriptionUpdateResult(
                subscription_id=request.subscription_id,
                success=True,
                videos_found=len(fetch_result.video_urls),
                videos_enqueued=enqueued,
                cursor_payload=fetch_result.cursor_payload,
                latest_video_url=fetch_result.latest_video_url,
                total_available=fetch_result.total_available,
            )
        except Exception as e:
            # 记录错误指标
            metrics.counter("subscription.update.total", tags={**tags, "status": "error"})
            metrics.counter("subscription.errors.total", tags={**tags, "error_type": type(e).__name__})
            if request.sync_state_id:
                subscription_sync_state_service.mark_sync_failed(request.sync_state_id, str(e))
            return SubscriptionUpdateResult(
                subscription_id=request.subscription_id,
                success=False,
                videos_found=0,
                videos_enqueued=0,
                error_message=str(e)
            )

