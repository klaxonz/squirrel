"""
队列积压监控器

用于检查特定订阅在视频提取队列中的积压情况
"""
import json
import logging
from typing import Dict, Optional

from core.cache import redis_client
from queue.queue_config import get_queue_config, QueueType, QueueMode
from utils import url_helper

logger = logging.getLogger()


class QueueBackpressureMonitor:
    """队列反压监控器"""
    
    def __init__(self):
        self.config = get_queue_config()
    
    def count_pending_videos_for_subscription(
        self, 
        subscription_id: int,
        url: str,
        check_limit: int = 1000
    ) -> int:
        """
        统计某个订阅在视频提取队列中待处理的视频数量
        
        Args:
            subscription_id: 订阅ID
            url: 订阅URL（用于确定队列）
            check_limit: 最多检查队列中最近的多少条消息（避免全量扫描）
            
        Returns:
            待处理的视频数量
        """
        try:
            # 确定该订阅对应的域队列（检查 incr 和 full 队列）
            domain = url_helper.extract_top_level_domain(url)
            site = self.config.get_site_by_domain(domain)
            
            if not site:
                logger.warning(f"Unknown site for domain: {domain}")
                return 0
            
            # 检查增量队列和全量队列
            total_count = 0
            
            for mode in [QueueMode.INCREMENTAL, QueueMode.FULL]:
                queue_name = self.config.build_queue_name(QueueType.VIDEO_EXTRACT, site, mode)
                count = self._count_in_queue(queue_name, subscription_id, check_limit)
                total_count += count
                
                if count > 0:
                    logger.debug(
                        f"Found {count} pending videos for subscription {subscription_id} "
                        f"in queue {queue_name}"
                    )
            
            return total_count
            
        except Exception as e:
            logger.error(f"Failed to count pending videos for subscription {subscription_id}: {e}")
            return 0  # 出错时返回0，不阻塞调度
    
    def _count_in_queue(
        self, 
        queue_name: str, 
        subscription_id: int,
        check_limit: int
    ) -> int:
        """
        统计指定队列中属于某个订阅的消息数量
        
        Args:
            queue_name: 队列名称
            subscription_id: 订阅ID
            check_limit: 最多检查多少条消息
            
        Returns:
            匹配的消息数量
        """
        try:
            # 使用 XREVRANGE 从新到旧读取（新消息更可能是待处理的）
            messages = redis_client.xrevrange(queue_name, '+', '-', count=check_limit)
            
            if not messages:
                return 0
            
            count = 0
            for msg_id, fields in messages:
                try:
                    # 解析消息体
                    body_str = fields.get(b'body') or fields.get('body')
                    if body_str is None:
                        continue
                    
                    if isinstance(body_str, bytes):
                        body_str = body_str.decode('utf-8')
                    
                    # 这里的body是message的body，需要再解析一次
                    message_body = json.loads(body_str)
                    
                    # VideoExtractDto 的结构
                    if isinstance(message_body, dict) and 'subscription_id' in message_body:
                        if message_body['subscription_id'] == subscription_id:
                            count += 1
                    
                except Exception as e:
                    logger.debug(f"Failed to parse message in queue {queue_name}: {e}")
                    continue
            
            return count
            
        except Exception as e:
            logger.error(f"Failed to scan queue {queue_name}: {e}")
            return 0
    
    def should_skip_subscription_update(
        self,
        subscription_id: int,
        url: str,
        threshold_ratio: float = 0.5,
        incremental_size: int = 30
    ) -> tuple[bool, Optional[int]]:
        """
        判断是否应该跳过本次订阅更新
        
        Args:
            subscription_id: 订阅ID
            url: 订阅URL
            threshold_ratio: 阈值比例（默认0.5，即超过一半）
            incremental_size: 增量更新的大小（默认30）
            
        Returns:
            (是否跳过, 队列中的数量)
        """
        pending_count = self.count_pending_videos_for_subscription(
            subscription_id, 
            url,
            check_limit=incremental_size * 2  # 检查2倍的数量，确保准确
        )
        
        threshold = int(incremental_size * threshold_ratio)
        should_skip = pending_count >= threshold
        
        if should_skip:
            logger.info(
                f"Skipping subscription {subscription_id} update: "
                f"pending={pending_count}, threshold={threshold} "
                f"(ratio={threshold_ratio}, size={incremental_size})"
            )
        
        return should_skip, pending_count


# 全局单例
queue_monitor = QueueBackpressureMonitor()
