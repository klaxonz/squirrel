"""
进度事件监听器
"""
import logging
from typing import Optional
from datetime import datetime

from .event import ProgressEvent, ProgressEventType
from .emitter import progress_emitter

logger = logging.getLogger()


class LogProgressListener:
    """日志监听器 - 将进度事件记录到日志"""
    
    def __call__(self, event: ProgressEvent) -> None:
        event_name = event.event_type.value
        
        if event.error:
            logger.error(
                f"[Progress] {event_name} - Error: {event.error}, "
                f"trace_id={event.trace_id}, url={event.url}"
            )
        elif event.total > 0:
            logger.info(
                f"[Progress] {event_name} - {event.progress_percentage}% "
                f"({event.current}/{event.total}), "
                f"trace_id={event.trace_id}, "
                f"subscription_id={event.subscription_id}"
            )
        else:
            logger.info(
                f"[Progress] {event_name} - {event.message or 'Started'}, "
                f"trace_id={event.trace_id}"
            )


class DatabaseProgressListener:
    """数据库监听器 - 将进度事件保存到数据库"""
    
    def __call__(self, event: ProgressEvent) -> None:
        try:
            from core.database import get_session
            from models.task.progress_record import ProgressRecord
            
            with get_session() as session:
                record = ProgressRecord()
                record.event_type = event.event_type.value
                record.trace_id = event.trace_id
                record.subscription_id = event.subscription_id
                record.video_id = event.video_id
                record.url = event.url
                record.current_count = event.current
                record.total_count = event.total
                record.progress_percentage = event.progress_percentage
                record.message = event.message
                record.error_message = event.error
                record.created_at = event.timestamp
                
                session.add(record)
                session.commit()
                
        except Exception as e:
            logger.error(f"Failed to save progress to database: {e}", exc_info=True)


class WebSocketProgressListener:
    """WebSocket监听器 - 通过WebSocket推送进度更新（待实现）"""
    
    def __init__(self, websocket_manager=None):
        self.websocket_manager = websocket_manager
    
    def __call__(self, event: ProgressEvent) -> None:
        if not self.websocket_manager:
            return
        
        try:
            # 推送给订阅了该trace_id的客户端
            if event.trace_id:
                self.websocket_manager.broadcast(
                    channel=f"progress:{event.trace_id}",
                    message=event.to_dict()
                )
            
            # 推送给订阅了该subscription的客户端
            if event.subscription_id:
                self.websocket_manager.broadcast(
                    channel=f"subscription:{event.subscription_id}",
                    message=event.to_dict()
                )
                
        except Exception as e:
            logger.error(f"Failed to push progress via WebSocket: {e}", exc_info=True)


def setup_default_listeners() -> None:
    """
    设置默认的监听器
    在应用启动时调用
    """
    # 注册日志监听器到所有事件
    log_listener = LogProgressListener()
    for event_type in ProgressEventType:
        progress_emitter.on(event_type, log_listener)
    
    # 注册数据库监听器到关键事件
    db_listener = DatabaseProgressListener()
    critical_events = [
        # 订阅更新相关
        ProgressEventType.SUBSCRIPTION_UPDATE_START,
        ProgressEventType.SUBSCRIPTION_UPDATE_COMPLETE,
        ProgressEventType.SUBSCRIPTION_UPDATE_ERROR,
        # 批量处理相关
        ProgressEventType.BATCH_PROCESS_START,
        ProgressEventType.BATCH_PROCESS_PROGRESS,
        ProgressEventType.BATCH_PROCESS_COMPLETE,
        # 视频提取相关（重要：记录每个视频的状态）
        ProgressEventType.VIDEO_EXTRACTION_START,
        ProgressEventType.VIDEO_EXTRACTION_COMPLETE,
        ProgressEventType.VIDEO_EXTRACTION_ERROR,
    ]
    for event_type in critical_events:
        progress_emitter.on(event_type, db_listener)
    
    logger.info("Progress listeners setup completed")

