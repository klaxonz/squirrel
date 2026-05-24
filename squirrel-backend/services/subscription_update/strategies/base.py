"""
订阅更新策略基类
每个站点可以实现自己的更新策略
"""
from abc import ABC, abstractmethod
from typing import Optional

from services.subscription_sync_event_service import SyncEventInput, append_event
from services.subscription_sync_run_service import SyncEventType, SyncPhase, SyncRunStatus
from services import subscription_sync_state_service
from utils.metrics import metrics
from ..models import SubscriptionUpdateRequest, SubscriptionUpdateResult, UpdateMode


def _append_request_event(
    request: SubscriptionUpdateRequest,
    event_type: str,
    event_phase: str,
    event_status: Optional[str],
    payload: Optional[dict] = None,
    message: Optional[str] = None,
) -> None:
    if not request.run_id:
        return
    append_event(
        SyncEventInput(
            stream_id=request.run_id,
            subscription_id=request.subscription_id,
            sync_state_id=request.sync_state_id,
            site=subscription_sync_state_service._resolve_site(request.url),
            sync_mode=request.mode.value,
            trigger=request.trigger.value,
            request_id=request.request_id,
            trace_id=request.trace_id,
            event_type=event_type,
            event_phase=event_phase,
            event_status=event_status,
            payload=payload,
            message=message,
        )
    )


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
                subscription_sync_state_service.mark_sync_skipped(
                    request.sync_state_id,
                    run_id=request.run_id,
                    request_id=request.request_id,
                    trace_id=request.trace_id,
                    trigger=request.trigger.value,
                    reason=skip_reason or 'unknown',
                )
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
            _append_request_event(
                request,
                SyncEventType.PHASE_CHANGED,
                SyncPhase.FETCHING_FEED,
                SyncRunStatus.RUNNING,
            )
            fetch_result = self.fetch_videos(request)
            _append_request_event(
                request,
                SyncEventType.PHASE_CHANGED,
                SyncPhase.CALCULATING_DELTA,
                SyncRunStatus.RUNNING,
                payload={
                    'source_video_count': fetch_result.source_video_count,
                    'videos_found': len(fetch_result.video_urls),
                    'latest_video_url': fetch_result.latest_video_url,
                },
            )
            
            _append_request_event(
                request,
                SyncEventType.PHASE_CHANGED,
                SyncPhase.ENQUEUEING,
                SyncRunStatus.RUNNING,
            )
            enqueued = self.enqueue_extraction(fetch_result, request)

            _append_request_event(
                request,
                SyncEventType.PHASE_CHANGED,
                SyncPhase.FINALIZING,
                SyncRunStatus.RUNNING,
                payload={
                    'source_video_count': fetch_result.source_video_count,
                    'videos_found': len(fetch_result.video_urls),
                    'videos_enqueued': enqueued,
                    'has_more': bool(getattr(fetch_result, 'has_more', False)),
                },
            )

            if request.sync_state_id:
                if request.mode == UpdateMode.FULL and bool(getattr(fetch_result, 'has_more', False)):
                    subscription_sync_state_service.continue_full_sync_batch(
                        request.sync_state_id,
                        cursor_payload=fetch_result.cursor_payload,
                        latest_video_url=fetch_result.latest_video_url,
                        source_video_count=fetch_result.source_video_count,
                        videos_found=len(fetch_result.video_urls),
                        videos_enqueued=enqueued,
                        run_id=request.run_id,
                        request_id=request.request_id,
                        trace_id=request.trace_id,
                        trigger=request.trigger.value,
                    )

                    from services.subscription_update import scheduler

                    if request.inline_video_extraction:
                        continuation_result = scheduler.run_one_inline(
                            subscription_id=request.subscription_id,
                            url=request.url,
                            trigger=request.trigger,
                            mode=request.mode,
                            user_id=request.user_id,
                            force=request.force,
                            trace_id=request.trace_id,
                            run_id=request.run_id,
                        )
                        expected_status = 'success'
                    else:
                        continuation_result = scheduler.schedule_one(
                            subscription_id=request.subscription_id,
                            url=request.url,
                            trigger=request.trigger,
                            mode=request.mode,
                            user_id=request.user_id,
                            force=request.force,
                            trace_id=request.trace_id,
                            run_id=request.run_id,
                        )
                        expected_status = 'queued'
                    if continuation_result.status != expected_status:
                        raise ValueError(
                            f'Failed to continue subscription sync: subscription_id={request.subscription_id}, '
                            f'status={continuation_result.status}'
                        )
                else:
                    subscription_sync_state_service.mark_sync_success(
                        request.sync_state_id,
                        cursor_payload=fetch_result.cursor_payload,
                        latest_video_url=fetch_result.latest_video_url,
                        source_video_count=fetch_result.source_video_count,
                        videos_found=len(fetch_result.video_urls),
                        videos_enqueued=enqueued,
                        run_id=request.run_id,
                        request_id=request.request_id,
                        trace_id=request.trace_id,
                        trigger=request.trigger.value,
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
                has_more=bool(getattr(fetch_result, 'has_more', False)),
                cursor_payload=fetch_result.cursor_payload,
                latest_video_url=fetch_result.latest_video_url,
                source_video_count=fetch_result.source_video_count,
                total_available=fetch_result.total_available,
                head_sample_urls=getattr(fetch_result, 'head_sample_urls', None),
                anchor_found=getattr(fetch_result, 'anchor_found', None),
                oldest_scanned_url=getattr(fetch_result, 'oldest_scanned_url', None),
                cursor_invalid=bool(getattr(fetch_result, 'cursor_invalid', False)),
                cursor_loop_detected=bool(getattr(fetch_result, 'cursor_loop_detected', False)),
                scan_depth=getattr(fetch_result, 'scan_depth', None),
            )
        except Exception as e:
            # 记录错误指标
            metrics.counter("subscription.update.total", tags={**tags, "status": "error"})
            metrics.counter("subscription.errors.total", tags={**tags, "error_type": type(e).__name__})
            if request.sync_state_id:
                subscription_sync_state_service.mark_sync_failed(
                    request.sync_state_id,
                    str(e),
                    run_id=request.run_id,
                    request_id=request.request_id,
                    trace_id=request.trace_id,
                    error_type=type(e).__name__,
                    trigger=request.trigger.value,
                )
            return SubscriptionUpdateResult(
                subscription_id=request.subscription_id,
                success=False,
                videos_found=0,
                videos_enqueued=0,
                error_message=str(e)
            )

