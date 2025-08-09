"""
队列注册表

维护队列和处理器的映射关系，支持精确匹配和模式匹配。
"""

import re
import logging
from typing import Dict, Callable, Any, List, Optional, Pattern
from .exceptions import PatternMatchError, HandlerRegistrationError, handle_queue_error

logger = logging.getLogger(__name__)


class QueueRegistry:
    """队列注册表
    
    负责维护队列名称与处理器的映射关系，支持：
    - 精确队列名称匹配
    - 通配符模式匹配
    - 动态队列创建
    - 处理器缓存
    """
    
    # 精确队列名称映射
    _exact_queues: Dict[str, Any] = {}
    _exact_handlers: Dict[str, Callable] = {}
    
    # 模式队列映射: [(pattern, compiled_regex, handler, actor_kwargs)]
    _pattern_queues: List[tuple] = []
    
    # 缓存已创建的动态队列，避免重复创建
    _dynamic_cache: Dict[str, Any] = {}
    
    @classmethod
    @handle_queue_error
    def register_queue(cls, queue_name: str, actor: Any, handler: Callable) -> None:
        """注册精确队列名称
        
        Args:
            queue_name: 队列名称
            actor: dramatiq actor对象
            handler: 处理函数
            
        Raises:
            HandlerRegistrationError: 注册失败时抛出
        """
        try:
            cls._exact_queues[queue_name] = actor
            cls._exact_handlers[queue_name] = handler
            logger.info(f"Registered exact queue: {queue_name}")
            
        except Exception as e:
            raise HandlerRegistrationError(
                handler_name=getattr(handler, '__name__', str(handler)),
                queue_pattern=queue_name,
                cause=e
            )
    
    @classmethod
    @handle_queue_error
    def register_pattern(cls, pattern: str, handler: Callable, **actor_kwargs) -> None:
        """注册队列模式
        
        Args:
            pattern: 队列模式，支持通配符 *
            handler: 处理函数
            **actor_kwargs: dramatiq actor参数
            
        Raises:
            PatternMatchError: 模式编译失败时抛出
            HandlerRegistrationError: 注册失败时抛出
        """
        try:
            # 将通配符模式转换为正则表达式
            regex_pattern = cls._convert_pattern_to_regex(pattern)
            compiled_regex = re.compile(f"^{regex_pattern}$")
            
            # 验证模式是否有效
            cls._validate_pattern(pattern, compiled_regex)
            
            cls._pattern_queues.append((pattern, compiled_regex, handler, actor_kwargs))
            logger.info(f"Registered pattern queue: {pattern} -> {regex_pattern}")
            
        except re.error as e:
            raise PatternMatchError(pattern, cause=e)
        except Exception as e:
            raise HandlerRegistrationError(
                handler_name=getattr(handler, '__name__', str(handler)),
                queue_pattern=pattern,
                cause=e
            )
    
    @classmethod
    def _convert_pattern_to_regex(cls, pattern: str) -> str:
        """将通配符模式转换为正则表达式
        
        Args:
            pattern: 通配符模式
            
        Returns:
            str: 正则表达式字符串
        """
        # 转义正则表达式特殊字符，但保留我们的通配符
        escaped = re.escape(pattern)
        
        # 将转义后的通配符替换为正则表达式
        regex_pattern = escaped.replace(r'\*', '.*').replace(r'\?', '.')
        
        return regex_pattern
    
    @classmethod
    def _validate_pattern(cls, pattern: str, compiled_regex: Pattern) -> None:
        """验证模式是否有效
        
        Args:
            pattern: 原始模式
            compiled_regex: 编译后的正则表达式
            
        Raises:
            PatternMatchError: 模式无效时抛出
        """
        # 检查模式是否过于宽泛
        if pattern == '*' or pattern == '.*':
            raise PatternMatchError(pattern, cause=ValueError("Pattern too broad"))
        
        # 测试模式是否能正常工作
        test_cases = [
            f"test_{pattern.replace('*', 'example')}",
            f"{pattern.replace('*', 'sample')}_queue"
        ]
        
        for test_case in test_cases:
            try:
                compiled_regex.match(test_case)
            except Exception as e:
                raise PatternMatchError(pattern, cause=e)
    
    @classmethod
    @handle_queue_error
    def get_actor(cls, queue_name: str) -> Optional[Any]:
        """获取队列对应的actor
        
        首先查找精确匹配，然后查找模式匹配，支持动态创建。
        
        Args:
            queue_name: 队列名称
            
        Returns:
            Optional[Any]: actor对象，不存在时返回None
        """
        # 1. 查找精确匹配
        if queue_name in cls._exact_queues:
            logger.debug(f"Found exact match for queue: {queue_name}")
            return cls._exact_queues[queue_name]
        
        # 2. 查找动态缓存
        if queue_name in cls._dynamic_cache:
            logger.debug(f"Found cached dynamic queue: {queue_name}")
            return cls._dynamic_cache[queue_name]
        
        # 3. 查找模式匹配
        for pattern, regex, handler, actor_kwargs in cls._pattern_queues:
            if regex.match(queue_name):
                logger.debug(f"Pattern match found: {queue_name} matches {pattern}")
                return cls._create_dynamic_actor(queue_name, handler, actor_kwargs, pattern)
        
        logger.debug(f"No match found for queue: {queue_name}")
        return None
    
    @classmethod
    def _create_dynamic_actor(cls, queue_name: str, handler: Callable, 
                            actor_kwargs: dict, pattern: str) -> Any:
        """动态创建actor
        
        Args:
            queue_name: 队列名称
            handler: 处理函数
            actor_kwargs: actor参数
            pattern: 匹配的模式
            
        Returns:
            Any: 创建的actor对象
        """
        try:
            import dramatiq
            
            # 为模式匹配的处理器创建包装函数
            def wrapper(msg, h=handler, qn=queue_name):
                return cls._call_handler_with_queue_name(h, msg, qn)
            
            # 设置包装函数的名称，便于调试
            wrapper.__name__ = f"{handler.__name__}_{queue_name.replace('*', 'dynamic')}"

            # 创建actor - 使用唯一actor名称避免冲突
            actor_name = f"{handler.__name__}__{queue_name}"
            actor = dramatiq.actor(queue_name=queue_name, actor_name=actor_name, **actor_kwargs)(wrapper)

            # 缓存创建的actor
            cls._dynamic_cache[queue_name] = actor
            cls._exact_handlers[queue_name] = handler

            logger.info(f"Dynamically created queue: {queue_name} (pattern: {pattern}), actor: {actor_name}")
            return actor
            
        except Exception as e:
            logger.error(f"Failed to create dynamic actor for {queue_name}: {e}")
            raise HandlerRegistrationError(
                handler_name=getattr(handler, '__name__', str(handler)),
                queue_pattern=pattern,
                cause=e
            )
    
    @classmethod
    def _call_handler_with_queue_name(cls, handler: Callable, message: Any, queue_name: str) -> Any:
        """调用处理器，根据签名决定是否传递queue_name参数
        
        Args:
            handler: 处理函数
            message: 消息
            queue_name: 队列名称
            
        Returns:
            Any: 处理结果
        """
        import inspect
        
        try:
            # 检查处理器是否接受queue_name参数
            sig = inspect.signature(handler)
            if 'queue_name' in sig.parameters:
                return handler(message, queue_name=queue_name)
            else:
                return handler(message)
                
        except Exception as e:
            logger.error(f"Error calling handler {handler.__name__} for queue {queue_name}: {e}")
            raise
    
    @classmethod
    def has_queue(cls, queue_name: str) -> bool:
        """检查队列是否存在
        
        Args:
            queue_name: 队列名称
            
        Returns:
            bool: 队列是否存在
        """
        return cls.get_actor(queue_name) is not None
    
    @classmethod
    def get_handler(cls, queue_name: str) -> Optional[Callable]:
        """获取队列对应的处理函数
        
        Args:
            queue_name: 队列名称
            
        Returns:
            Optional[Callable]: 处理函数，不存在时返回None
        """
        # 确保队列存在（可能需要动态创建）
        cls.get_actor(queue_name)
        
        return cls._exact_handlers.get(queue_name)
    
    @classmethod
    def get_all_info(cls) -> Dict[str, Any]:
        """获取所有队列信息
        
        Returns:
            Dict[str, Any]: 队列统计信息
        """
        return {
            "exact_queues": list(cls._exact_queues.keys()),
            "pattern_queues": [pattern for pattern, _, _, _ in cls._pattern_queues],
            "dynamic_queues": list(cls._dynamic_cache.keys()),
            "total_exact": len(cls._exact_queues),
            "total_patterns": len(cls._pattern_queues),
            "total_dynamic": len(cls._dynamic_cache),
            "total_handlers": len(cls._exact_handlers)
        }
    
    @classmethod
    def clear_cache(cls) -> None:
        """清空动态队列缓存
        
        用于测试或重置系统状态。
        """
        cls._dynamic_cache.clear()
        logger.info("Cleared dynamic queue cache")
    
    @classmethod
    def get_matching_patterns(cls, queue_name: str) -> List[str]:
        """获取匹配指定队列名称的所有模式
        
        Args:
            queue_name: 队列名称
            
        Returns:
            List[str]: 匹配的模式列表
        """
        matching_patterns = []
        for pattern, regex, _, _ in cls._pattern_queues:
            if regex.match(queue_name):
                matching_patterns.append(pattern)
        
        return matching_patterns
    
    @classmethod
    def validate_queue_name(cls, queue_name: str) -> bool:
        """验证队列名称是否有效
        
        Args:
            queue_name: 队列名称
            
        Returns:
            bool: 队列名称是否有效
        """
        if not queue_name or not isinstance(queue_name, str):
            return False
        
        # 检查队列名称格式
        if not re.match(r'^[a-zA-Z0-9_\-]+$', queue_name):
            return False
        
        # 检查长度限制
        if len(queue_name) > 255:
            return False
        
        return True
