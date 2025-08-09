"""
消息路由器

根据消息内容智能路由到合适的队列。
"""

import logging
from typing import Callable, Dict, Any, Optional, List
from .manager import QueueManager
from .exceptions import RoutingError, handle_queue_error

logger = logging.getLogger(__name__)


class MessageRouter:
    """消息路由器
    
    根据预定义的路由规则，智能地将消息路由到合适的队列。
    支持：
    - 基于消息内容的路由
    - 复杂的路由逻辑
    - 路由规则链
    - 默认路由和回退机制
    """
    
    # 路由规则映射: rule_name -> routing_function
    _routing_rules: Dict[str, Callable] = {}
    
    # 路由统计信息
    _stats = {
        "rules_registered": 0,
        "messages_routed": 0,
        "routing_errors": 0,
        "rule_usage": {}  # rule_name -> usage_count
    }
    
    @classmethod
    @handle_queue_error
    def register_rule(cls, rule_name: str, routing_func: Callable[[Any], str]) -> None:
        """注册路由规则
        
        Args:
            rule_name: 路由规则名称
            routing_func: 路由函数，接收消息返回队列名称
            
        Raises:
            RoutingError: 注册失败时抛出
            
        Examples:
            def video_routing(message):
                url = message.get('url', '')
                if 'bilibili.com' in url:
                    return 'video_extract_bilibili'
                return 'video_extract_default'
            
            MessageRouter.register_rule("video_processing", video_routing)
        """
        try:
            # 验证参数
            cls._validate_rule_registration(rule_name, routing_func)
            
            # 注册规则
            cls._routing_rules[rule_name] = routing_func
            cls._stats["rules_registered"] += 1
            cls._stats["rule_usage"][rule_name] = 0
            
            logger.info(f"Registered routing rule: {rule_name}")
            
        except Exception as e:
            logger.error(f"Failed to register routing rule {rule_name}: {e}")
            raise RoutingError(
                f"Failed to register routing rule: {rule_name}",
                rule_name=rule_name,
                cause=e
            )
    
    @classmethod
    def _validate_rule_registration(cls, rule_name: str, routing_func: Callable) -> None:
        """验证路由规则注册参数
        
        Args:
            rule_name: 规则名称
            routing_func: 路由函数
            
        Raises:
            ValueError: 参数无效时抛出
        """
        if not rule_name or not isinstance(rule_name, str):
            raise ValueError("rule_name must be a non-empty string")
        
        if not callable(routing_func):
            raise ValueError("routing_func must be callable")
        
        # 检查函数签名
        import inspect
        try:
            sig = inspect.signature(routing_func)
            if len(sig.parameters) < 1:
                raise ValueError("routing_func must accept at least one parameter (message)")
        except Exception as e:
            logger.warning(f"Could not validate function signature for {rule_name}: {e}")
    
    @classmethod
    @handle_queue_error
    def route_message(cls, rule_name: str, message: Any) -> str:
        """根据规则路由消息
        
        Args:
            rule_name: 路由规则名称
            message: 要路由的消息
            
        Returns:
            str: 目标队列名称
            
        Raises:
            RoutingError: 路由规则不存在或执行失败时抛出
        """
        if rule_name not in cls._routing_rules:
            available_rules = list(cls._routing_rules.keys())
            raise RoutingError(
                f"Routing rule not found: {rule_name}. Available rules: {available_rules}",
                rule_name=rule_name,
                original_message=message
            )
        
        try:
            routing_func = cls._routing_rules[rule_name]
            queue_name = routing_func(message)
            
            # 验证返回的队列名称
            if not queue_name or not isinstance(queue_name, str):
                raise RoutingError(
                    f"Routing rule {rule_name} returned invalid queue name: {queue_name}",
                    rule_name=rule_name,
                    original_message=message
                )
            
            # 更新统计信息
            cls._stats["rule_usage"][rule_name] += 1
            
            logger.debug(f"Routed message to queue: {queue_name} (rule: {rule_name})")
            return queue_name
            
        except RoutingError:
            cls._stats["routing_errors"] += 1
            raise
        except Exception as e:
            cls._stats["routing_errors"] += 1
            logger.error(f"Error in routing rule {rule_name}: {e}")
            raise RoutingError(
                f"Error executing routing rule: {rule_name}",
                rule_name=rule_name,
                original_message=message,
                cause=e
            )
    
    @classmethod
    @handle_queue_error
    def send_with_routing(cls, rule_name: str, message: Any) -> str:
        """使用路由规则发送消息
        
        Args:
            rule_name: 路由规则名称
            message: 要发送的消息
            
        Returns:
            str: 实际发送到的队列名称
            
        Raises:
            RoutingError: 路由失败时抛出
            QueueNotFoundError: 目标队列不存在时抛出
            MessageSendError: 消息发送失败时抛出
        """
        try:
            # 路由消息
            queue_name = cls.route_message(rule_name, message)
            
            # 发送消息
            QueueManager.send_message(queue_name, message)
            
            cls._stats["messages_routed"] += 1
            logger.debug(f"Message routed and sent: {rule_name} -> {queue_name}")
            
            return queue_name
            
        except Exception as e:
            cls._stats["routing_errors"] += 1
            logger.error(f"Failed to route and send message with rule {rule_name}: {e}")
            raise
    
    @classmethod
    def send_with_routing_safe(cls, rule_name: str, message: Any, 
                              fallback_queue: Optional[str] = None) -> Optional[str]:
        """安全地使用路由规则发送消息，失败时不抛出异常
        
        Args:
            rule_name: 路由规则名称
            message: 要发送的消息
            fallback_queue: 备用队列名称
            
        Returns:
            Optional[str]: 实际发送到的队列名称，失败时返回None
        """
        try:
            return cls.send_with_routing(rule_name, message)
        except Exception as e:
            logger.error(f"Routing failed for rule {rule_name}: {e}")
            
            if fallback_queue:
                try:
                    QueueManager.send_message(fallback_queue, message)
                    logger.warning(f"Message sent to fallback queue {fallback_queue} "
                                 f"(routing rule {rule_name} failed)")
                    return fallback_queue
                except Exception as fallback_error:
                    logger.error(f"Fallback queue {fallback_queue} also failed: {fallback_error}")
            
            return None
    
    @classmethod
    def batch_route_messages(cls, rule_name: str, messages: List[Any]) -> Dict[str, Any]:
        """批量路由消息
        
        Args:
            rule_name: 路由规则名称
            messages: 消息列表
            
        Returns:
            Dict[str, Any]: 路由结果统计
        """
        results = {
            "total": len(messages),
            "success": 0,
            "failed": 0,
            "queue_distribution": {},  # queue_name -> count
            "errors": []
        }
        
        for i, message in enumerate(messages):
            try:
                queue_name = cls.send_with_routing(rule_name, message)
                results["success"] += 1
                
                # 统计队列分布
                if queue_name in results["queue_distribution"]:
                    results["queue_distribution"][queue_name] += 1
                else:
                    results["queue_distribution"][queue_name] = 1
                    
            except Exception as e:
                results["failed"] += 1
                results["errors"].append({
                    "index": i,
                    "message": message,
                    "error": str(e)
                })
                logger.error(f"Failed to route message {i} with rule {rule_name}: {e}")
        
        logger.info(f"Batch routing with {rule_name}: {results['success']}/{results['total']} successful")
        return results
    
    @classmethod
    def create_composite_rule(cls, rule_name: str, rules: List[str], 
                            strategy: str = "first_match") -> None:
        """创建复合路由规则
        
        Args:
            rule_name: 新规则名称
            rules: 组成规则列表
            strategy: 组合策略 ("first_match", "priority", "round_robin")
            
        Raises:
            RoutingError: 创建失败时抛出
        """
        def composite_routing_func(message):
            if strategy == "first_match":
                # 使用第一个匹配的规则
                for sub_rule in rules:
                    try:
                        return cls.route_message(sub_rule, message)
                    except RoutingError:
                        continue
                raise RoutingError(f"No matching rule found in composite rule {rule_name}")
            
            elif strategy == "priority":
                # 按优先级顺序尝试规则
                for sub_rule in rules:
                    try:
                        return cls.route_message(sub_rule, message)
                    except RoutingError:
                        continue
                raise RoutingError(f"All rules failed in composite rule {rule_name}")
            
            elif strategy == "round_robin":
                # 轮询规则（简单实现）
                import random
                sub_rule = random.choice(rules)
                return cls.route_message(sub_rule, message)
            
            else:
                raise RoutingError(f"Unknown composite strategy: {strategy}")
        
        cls.register_rule(rule_name, composite_routing_func)
        logger.info(f"Created composite rule {rule_name} with strategy {strategy}")
    
    @classmethod
    def get_routing_stats(cls) -> Dict[str, Any]:
        """获取路由统计信息
        
        Returns:
            Dict[str, Any]: 路由统计信息
        """
        return {
            **cls._stats,
            "available_rules": list(cls._routing_rules.keys()),
            "total_rules": len(cls._routing_rules)
        }
    
    @classmethod
    def get_rule_info(cls, rule_name: str) -> Dict[str, Any]:
        """获取特定路由规则的信息
        
        Args:
            rule_name: 规则名称
            
        Returns:
            Dict[str, Any]: 规则信息
        """
        if rule_name not in cls._routing_rules:
            return {"exists": False}
        
        routing_func = cls._routing_rules[rule_name]
        
        info = {
            "exists": True,
            "rule_name": rule_name,
            "usage_count": cls._stats["rule_usage"].get(rule_name, 0),
            "function_name": getattr(routing_func, '__name__', 'unknown')
        }
        
        # 尝试获取函数签名信息
        try:
            import inspect
            sig = inspect.signature(routing_func)
            info["parameters"] = list(sig.parameters.keys())
            info["has_docstring"] = bool(routing_func.__doc__)
            if routing_func.__doc__:
                info["docstring"] = routing_func.__doc__.strip()
        except Exception as e:
            info["signature_error"] = str(e)
        
        return info
    
    @classmethod
    def test_routing_rule(cls, rule_name: str, test_messages: List[Any]) -> Dict[str, Any]:
        """测试路由规则
        
        Args:
            rule_name: 规则名称
            test_messages: 测试消息列表
            
        Returns:
            Dict[str, Any]: 测试结果
        """
        if rule_name not in cls._routing_rules:
            return {"error": f"Rule {rule_name} not found"}
        
        results = {
            "rule_name": rule_name,
            "test_count": len(test_messages),
            "results": [],
            "success_count": 0,
            "error_count": 0,
            "unique_queues": set()
        }
        
        for i, message in enumerate(test_messages):
            try:
                queue_name = cls.route_message(rule_name, message)
                results["results"].append({
                    "index": i,
                    "message": message,
                    "queue_name": queue_name,
                    "success": True
                })
                results["success_count"] += 1
                results["unique_queues"].add(queue_name)
                
            except Exception as e:
                results["results"].append({
                    "index": i,
                    "message": message,
                    "error": str(e),
                    "success": False
                })
                results["error_count"] += 1
        
        results["unique_queues"] = list(results["unique_queues"])
        results["success_rate"] = results["success_count"] / len(test_messages) if test_messages else 0
        
        return results
    
    @classmethod
    def reset_stats(cls) -> None:
        """重置路由统计信息"""
        cls._stats = {
            "rules_registered": len(cls._routing_rules),
            "messages_routed": 0,
            "routing_errors": 0,
            "rule_usage": {rule: 0 for rule in cls._routing_rules.keys()}
        }
        logger.info("Message router stats reset")
    
    @classmethod
    def clear_rules(cls) -> None:
        """清空所有路由规则（主要用于测试）"""
        cls._routing_rules.clear()
        cls._stats = {
            "rules_registered": 0,
            "messages_routed": 0,
            "routing_errors": 0,
            "rule_usage": {}
        }
        logger.warning("All routing rules cleared")
