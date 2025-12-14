"""
Pipeline上下文 - 在各个Stage之间传递数据
"""
from dataclasses import dataclass, field
from typing import Optional, List, Any, Dict
from datetime import datetime

from crawl import ExtractionTask, VideoMeta
from ..dto import VideoDTO


@dataclass
class PipelineContext:
    """
    Pipeline执行上下文
    
    在Pipeline的各个Stage之间传递数据和状态。
    每个Stage可以读取/修改context中的数据。
    """
    
    # ========== 输入 ==========
    task: ExtractionTask
    
    # ========== 中间数据（各Stage填充） ==========
    plugin_video: Optional[VideoMeta] = None              # ExtractionStage填充
    video_dto: Optional[VideoDTO] = None              # ValidationStage填充
    video_model: Optional[Any] = None                 # PersistenceStage填充（VideoModel）
    
    # ========== 元数据 ==========
    start_time: datetime = field(default_factory=datetime.now)
    current_stage: str = "init"
    errors: List[str] = field(default_factory=list)
    
    # ========== 控制标志 ==========
    should_skip_persistence: bool = False      # 是否跳过持久化
    should_skip_post_process: bool = False     # 是否跳过后处理
    
    # ========== 额外数据 ==========
    extra: Dict[str, Any] = field(default_factory=dict)  # 存储额外数据
    
    def add_error(self, stage: str, error: str):
        """添加错误信息"""
        self.errors.append(f"[{stage}] {error}")
    
    def has_errors(self) -> bool:
        """是否有错误"""
        return len(self.errors) > 0
    
    def get_duration(self) -> float:
        """获取执行时长（秒）"""
        return (datetime.now() - self.start_time).total_seconds()
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典（用于日志）"""
        return {
            'task_id': self.task.task_id,
            'url': self.task.url,
            'current_stage': self.current_stage,
            'duration': self.get_duration(),
            'has_plugin_video': self.plugin_video is not None,
            'has_video_dto': self.video_dto is not None,
            'has_video_model': self.video_model is not None,
            'errors_count': len(self.errors),
            'errors': self.errors,
        }
    
    def __repr__(self):
        return (
            f"PipelineContext("
            f"task_id={self.task.task_id}, "
            f"stage={self.current_stage}, "
            f"duration={self.get_duration():.2f}s)"
        )
