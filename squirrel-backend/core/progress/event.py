"""
进度事件定义
"""
from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, Dict, Any
from datetime import datetime


class ProgressEventType(Enum):
    """进度事件类型"""
    # 订阅更新相关
    SUBSCRIPTION_UPDATE_START = "subscription_update_start"
    SUBSCRIPTION_UPDATE_COMPLETE = "subscription_update_complete"
    SUBSCRIPTION_UPDATE_ERROR = "subscription_update_error"
    
    # 视频提取相关
    VIDEO_EXTRACTION_START = "video_extraction_start"
    VIDEO_EXTRACTION_COMPLETE = "video_extraction_complete"
    VIDEO_EXTRACTION_ERROR = "video_extraction_error"
    
    # 批量处理相关
    BATCH_PROCESS_START = "batch_process_start"
    BATCH_PROCESS_PROGRESS = "batch_process_progress"
    BATCH_PROCESS_COMPLETE = "batch_process_complete"
    
    # 下载相关
    DOWNLOAD_START = "download_start"
    DOWNLOAD_PROGRESS = "download_progress"
    DOWNLOAD_COMPLETE = "download_complete"
    DOWNLOAD_ERROR = "download_error"


@dataclass
class ProgressEvent:
    """进度事件"""
    event_type: ProgressEventType
    trace_id: Optional[str] = None
    subscription_id: Optional[int] = None
    video_id: Optional[int] = None
    url: Optional[str] = None
    
    # 进度信息
    current: int = 0
    total: int = 0
    
    # 附加数据
    message: Optional[str] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # 时间戳
    timestamp: datetime = field(default_factory=datetime.now)
    
    @property
    def progress_percentage(self) -> float:
        """计算进度百分比"""
        if self.total == 0:
            return 0.0
        return round((self.current / self.total) * 100, 2)
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            'event_type': self.event_type.value,
            'trace_id': self.trace_id,
            'subscription_id': self.subscription_id,
            'video_id': self.video_id,
            'url': self.url,
            'current': self.current,
            'total': self.total,
            'progress_percentage': self.progress_percentage,
            'message': self.message,
            'error': self.error,
            'metadata': self.metadata,
            'timestamp': self.timestamp.isoformat()
        }

