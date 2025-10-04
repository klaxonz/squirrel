"""
默认更新策略（适用于所有站点）
"""
import logging
from typing import List, Optional
from sqlalchemy import update
from core.cache import get_distributed_lock
from core.config import settings
from core.database import get_session
from core.progress import progress_emitter, ProgressEvent, ProgressEventType
from crawl import SubscriptionFactory
from models.subscription import Subscription
from schemas.video.dto.video_dto import VideoExtractDto
from services import download_service, subscription_service
from .base import UpdateStrategy
from ..models import SubscriptionUpdateRequest, UpdateMode, UpdateTrigger

logger = logging.getLogger()


class DefaultUpdateStrategy(UpdateStrategy):
    """默认更新策略（适用于所有站点）"""
    
    def __init__(self):
        self._lock = None
    
    @property
    def site_name(self) -> str:
        return "default"
    
    def should_update(self, request: SubscriptionUpdateRequest) -> tuple[bool, Optional[str]]:
        """检查是否需要更新"""
        sub = subscription_service.get_subscription_detail(request.subscription_id)
        if not sub or sub.is_deleted:
            return False, "subscription_not_found"
        
        if not request.force:
            lock_key = f"lock:subscription:update:{request.subscription_id}"
            self._lock = get_distributed_lock(lock_key, timeout=180, auto_renewal=True)
            if not self._lock.acquire(blocking=False):
                return False, "update_in_progress"
        
        return True, None
    
    def fetch_videos(self, request: SubscriptionUpdateRequest) -> List[str]:
        """获取视频列表"""
        sub = subscription_service.get_subscription_detail(request.subscription_id)
        
        subscribe_channel = SubscriptionFactory.create_subscription(request.url)
        
        is_extract_all = self._should_extract_all(sub, request.mode)
        
        video_list = subscribe_channel.get_subscribe_videos(extract_all=is_extract_all)
        
        if is_extract_all and video_list:
            self._update_total_videos(request.subscription_id, len(video_list))
        
        if is_extract_all:
            return video_list
        else:
            return video_list[:settings.CHANNEL_UPDATE_DEFAULT_SIZE]
    
    def enqueue_extraction(self, video_urls: List[str], request: SubscriptionUpdateRequest) -> int:
        """将视频加入提取队列"""
        enqueued = 0
        is_manual = request.trigger == UpdateTrigger.MANUAL
        total = len(video_urls)
        
        # 发射批量处理开始事件
        progress_emitter.emit(ProgressEvent(
            event_type=ProgressEventType.BATCH_PROCESS_START,
            trace_id=request.trace_id,
            subscription_id=request.subscription_id,
            url=request.url,
            current=0,
            total=total,
            message=f"开始处理 {total} 个视频"
        ))
        
        for index, video_url in enumerate(video_urls, 1):
            try:
                params = VideoExtractDto(
                    url=video_url,
                    subscribed=True,
                    only_extract=True,
                    subscription_id=request.subscription_id,
                    is_manual=is_manual,
                    is_extract_all=False
                )
                
                # 发出视频提取开始事件（入队时）
                progress_emitter.emit(ProgressEvent(
                    event_type=ProgressEventType.VIDEO_EXTRACTION_START,
                    trace_id=request.trace_id,
                    subscription_id=request.subscription_id,
                    url=video_url,
                    message=f"视频入队: {video_url}"
                ))
                
                download_service.enqueue_video_extraction(params)
                enqueued += 1
                
                # 每处理 10 个视频或处理完毕时发射进度事件
                if index % 10 == 0 or index == total:
                    progress_emitter.emit(ProgressEvent(
                        event_type=ProgressEventType.BATCH_PROCESS_PROGRESS,
                        trace_id=request.trace_id,
                        subscription_id=request.subscription_id,
                        url=request.url,
                        current=index,
                        total=total,
                        message=f"已处理 {index}/{total} 个视频"
                    ))
                    
            except Exception as e:
                logger.warning(f"Failed to enqueue video {video_url}: {e}")
        
        # 发射批量处理完成事件
        progress_emitter.emit(ProgressEvent(
            event_type=ProgressEventType.BATCH_PROCESS_COMPLETE,
            trace_id=request.trace_id,
            subscription_id=request.subscription_id,
            url=request.url,
            current=enqueued,
            total=total,
            message=f"处理完成，成功 {enqueued}/{total} 个视频"
        ))
        
        return enqueued
    
    def execute(self, request: SubscriptionUpdateRequest) -> 'SubscriptionUpdateResult':
        """执行更新流程（覆盖以支持锁释放）"""
        try:
            return super().execute(request)
        finally:
            if self._lock:
                try:
                    self._lock.release()
                except Exception as e:
                    logger.warning(f"Failed to release lock for subscription {request.subscription_id}: {e}")
    
    @staticmethod
    def _should_extract_all(sub, mode: UpdateMode) -> bool:
        """判断是否全量提取"""
        if mode == UpdateMode.FULL:
            return True
        if mode == UpdateMode.INCREMENTAL:
            return False
        
        if sub.total_videos <= 0:
            return True
        if sub.total_extract >= sub.total_videos:
            return True
        if (sub.total_videos - sub.total_extract) >= settings.CHANNEL_UPDATE_DEFAULT_SIZE:
            return True
        return False
    
    @staticmethod
    def _update_total_videos(subscription_id: int, total: int) -> None:
        """更新订阅总视频数"""
        with get_session() as session:
            session.execute(
                update(Subscription)
                .where(Subscription.id == subscription_id)
                .values(total_videos=total)
            )

