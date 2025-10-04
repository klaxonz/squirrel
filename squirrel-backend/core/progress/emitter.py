"""
进度事件发射器
"""
import logging
from typing import Callable, List, Dict, Optional
from .event import ProgressEvent, ProgressEventType

logger = logging.getLogger()


class ProgressEmitter:
    """
    进度事件发射器（单例模式）
    负责管理监听器并分发事件
    """
    
    _instance = None
    _listeners: Dict[ProgressEventType, List[Callable[[ProgressEvent], None]]] = {}
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._listeners = {}
        return cls._instance
    
    def on(self, event_type: ProgressEventType, listener: Callable[[ProgressEvent], None]) -> None:
        """
        注册事件监听器
        
        Args:
            event_type: 事件类型
            listener: 监听器函数
        """
        if event_type not in self._listeners:
            self._listeners[event_type] = []
        
        if listener not in self._listeners[event_type]:
            self._listeners[event_type].append(listener)
            logger.debug(f"Registered listener for {event_type.value}")
    
    def off(self, event_type: ProgressEventType, listener: Callable[[ProgressEvent], None]) -> None:
        """
        移除事件监听器
        
        Args:
            event_type: 事件类型
            listener: 监听器函数
        """
        if event_type in self._listeners and listener in self._listeners[event_type]:
            self._listeners[event_type].remove(listener)
            logger.debug(f"Removed listener for {event_type.value}")
    
    def emit(self, event: ProgressEvent) -> None:
        """
        发射事件
        
        Args:
            event: 进度事件
        """
        event_type = event.event_type
        
        if event_type not in self._listeners:
            return
        
        for listener in self._listeners[event_type]:
            try:
                listener(event)
            except Exception as e:
                logger.error(f"Error in progress listener for {event_type.value}: {e}", exc_info=True)
    
    def emit_all(self, event: ProgressEvent) -> None:
        """
        发射事件到所有监听器（不区分事件类型）
        
        Args:
            event: 进度事件
        """
        for listeners in self._listeners.values():
            for listener in listeners:
                try:
                    listener(event)
                except Exception as e:
                    logger.error(f"Error in progress listener: {e}", exc_info=True)
    
    def clear(self, event_type: Optional[ProgressEventType] = None) -> None:
        """
        清除监听器
        
        Args:
            event_type: 事件类型，如果为None则清除所有
        """
        if event_type:
            self._listeners[event_type] = []
        else:
            self._listeners = {}


# 全局单例
progress_emitter = ProgressEmitter()

