"""
进度跟踪器实现
"""
import logging
from typing import Dict, Any, Optional
from datetime import datetime

from .interfaces import IProgressTracker
from .cache import ICacheManager, CacheKeys

logger = logging.getLogger(__name__)


class RedisProgressTracker(IProgressTracker):
    """基于Redis的进度跟踪器"""
    
    def __init__(self, cache_manager: ICacheManager, ttl: int = 3600):
        self.cache_manager = cache_manager
        self.ttl = ttl
    
    def start_task(self, task_id: str, total_steps: int = 1) -> None:
        """开始任务"""
        try:
            progress_data = {
                'task_id': task_id,
                'status': 'running',
                'current_step': 0,
                'total_steps': total_steps,
                'message': '任务开始',
                'start_time': datetime.now().isoformat(),
                'last_update': datetime.now().isoformat()
            }
            
            cache_key = CacheKeys.format_key(CacheKeys.TASK_PROGRESS, task_id=task_id)
            self.cache_manager.set(cache_key, progress_data, self.ttl)
            
            logger.debug(f"开始任务跟踪: {task_id}")
            
        except Exception as e:
            logger.error(f"开始任务跟踪失败: {task_id}, error: {e}")
    
    def update_progress(self, task_id: str, current_step: int, message: str = "") -> None:
        """更新进度"""
        try:
            cache_key = CacheKeys.format_key(CacheKeys.TASK_PROGRESS, task_id=task_id)
            progress_data = self.cache_manager.get(cache_key)
            
            if not progress_data:
                logger.warning(f"任务进度数据不存在: {task_id}")
                return
            
            progress_data.update({
                'current_step': current_step,
                'message': message,
                'last_update': datetime.now().isoformat()
            })
            
            self.cache_manager.set(cache_key, progress_data, self.ttl)
            logger.debug(f"更新任务进度: {task_id}, step: {current_step}, message: {message}")
            
        except Exception as e:
            logger.error(f"更新任务进度失败: {task_id}, error: {e}")
    
    def complete_task(self, task_id: str, success: bool = True) -> None:
        """完成任务"""
        try:
            cache_key = CacheKeys.format_key(CacheKeys.TASK_PROGRESS, task_id=task_id)
            progress_data = self.cache_manager.get(cache_key)
            
            if not progress_data:
                logger.warning(f"任务进度数据不存在: {task_id}")
                return
            
            progress_data.update({
                'status': 'completed' if success else 'failed',
                'current_step': progress_data.get('total_steps', 1),
                'message': '任务完成' if success else '任务失败',
                'end_time': datetime.now().isoformat(),
                'last_update': datetime.now().isoformat()
            })
            
            # 延长TTL以便查看结果
            self.cache_manager.set(cache_key, progress_data, self.ttl * 2)
            
            logger.debug(f"完成任务跟踪: {task_id}, success: {success}")
            
        except Exception as e:
            logger.error(f"完成任务跟踪失败: {task_id}, error: {e}")
    
    def get_progress(self, task_id: str) -> Optional[Dict[str, Any]]:
        """获取进度信息"""
        try:
            cache_key = CacheKeys.format_key(CacheKeys.TASK_PROGRESS, task_id=task_id)
            return self.cache_manager.get(cache_key)
        except Exception as e:
            logger.error(f"获取任务进度失败: {task_id}, error: {e}")
            return None
    
    def get_progress_percentage(self, task_id: str) -> float:
        """获取进度百分比"""
        progress_data = self.get_progress(task_id)
        if not progress_data:
            return 0.0
        
        current = progress_data.get('current_step', 0)
        total = progress_data.get('total_steps', 1)
        
        if total <= 0:
            return 0.0
        
        return min(100.0, (current / total) * 100.0)
    
    def cleanup_completed_tasks(self, older_than_hours: int = 24) -> int:
        """清理已完成的任务"""
        try:
            # 这里应该实现清理逻辑，但需要Redis支持
            # 暂时返回0，实际实现需要扫描所有进度键
            logger.info(f"清理{older_than_hours}小时前的已完成任务")
            return 0
        except Exception as e:
            logger.error(f"清理已完成任务失败: {e}")
            return 0


class MemoryProgressTracker(IProgressTracker):
    """基于内存的进度跟踪器（用于测试）"""
    
    def __init__(self):
        self._progress_data: Dict[str, Dict[str, Any]] = {}
    
    def start_task(self, task_id: str, total_steps: int = 1) -> None:
        """开始任务"""
        self._progress_data[task_id] = {
            'task_id': task_id,
            'status': 'running',
            'current_step': 0,
            'total_steps': total_steps,
            'message': '任务开始',
            'start_time': datetime.now().isoformat(),
            'last_update': datetime.now().isoformat()
        }
    
    def update_progress(self, task_id: str, current_step: int, message: str = "") -> None:
        """更新进度"""
        if task_id in self._progress_data:
            self._progress_data[task_id].update({
                'current_step': current_step,
                'message': message,
                'last_update': datetime.now().isoformat()
            })
    
    def complete_task(self, task_id: str, success: bool = True) -> None:
        """完成任务"""
        if task_id in self._progress_data:
            self._progress_data[task_id].update({
                'status': 'completed' if success else 'failed',
                'current_step': self._progress_data[task_id].get('total_steps', 1),
                'message': '任务完成' if success else '任务失败',
                'end_time': datetime.now().isoformat(),
                'last_update': datetime.now().isoformat()
            })
    
    def get_progress(self, task_id: str) -> Optional[Dict[str, Any]]:
        """获取进度信息"""
        return self._progress_data.get(task_id)
    
    def clear_all(self) -> None:
        """清空所有进度数据"""
        self._progress_data.clear()


class CompositeProgressTracker(IProgressTracker):
    """组合进度跟踪器，支持多个后端"""
    
    def __init__(self, *trackers: IProgressTracker):
        self.trackers = trackers
    
    def start_task(self, task_id: str, total_steps: int = 1) -> None:
        """开始任务"""
        for tracker in self.trackers:
            try:
                tracker.start_task(task_id, total_steps)
            except Exception as e:
                logger.error(f"进度跟踪器启动任务失败: {type(tracker).__name__}, error: {e}")
    
    def update_progress(self, task_id: str, current_step: int, message: str = "") -> None:
        """更新进度"""
        for tracker in self.trackers:
            try:
                tracker.update_progress(task_id, current_step, message)
            except Exception as e:
                logger.error(f"进度跟踪器更新进度失败: {type(tracker).__name__}, error: {e}")
    
    def complete_task(self, task_id: str, success: bool = True) -> None:
        """完成任务"""
        for tracker in self.trackers:
            try:
                tracker.complete_task(task_id, success)
            except Exception as e:
                logger.error(f"进度跟踪器完成任务失败: {type(tracker).__name__}, error: {e}")
    
    def get_progress(self, task_id: str) -> Optional[Dict[str, Any]]:
        """获取进度信息（从第一个可用的跟踪器）"""
        for tracker in self.trackers:
            try:
                progress = tracker.get_progress(task_id)
                if progress:
                    return progress
            except Exception as e:
                logger.error(f"进度跟踪器获取进度失败: {type(tracker).__name__}, error: {e}")
        return None
