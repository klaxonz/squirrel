import logging

from services.crawl_tasks import service as crawl_task_service

logger = logging.getLogger(__name__)


class QueueBackpressureMonitor:
    """队列反压监控器"""

    def count_pending_videos_for_subscription(
        self,
        subscription_id: int,
        url: str,
        check_limit: int = 1000,
    ) -> int:
        """统计某个订阅在视频提取队列中待处理的视频数量

        Args:
            subscription_id: 订阅ID
            url: 订阅URL（用于确定队列）
            check_limit: 最多检查队列中最近的多少条消息（避免全量扫描）

        Returns:
            待处理的视频数量

        """
        try:
            return crawl_task_service.count_pending_video_tasks_for_subscription(subscription_id)
        except (ConnectionError, OSError, ValueError, TypeError) as e:
            logger.error(f"Failed to count pending videos for subscription {subscription_id}: {e}")
            return 0

    def should_skip_subscription_update(
        self,
        subscription_id: int,
        url: str,
        threshold_ratio: float = 0.5,
        incremental_size: int = 30,
    ) -> tuple[bool, int | None]:
        """判断是否应该跳过本次订阅更新

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
            check_limit=incremental_size * 2,  # 检查2倍的数量，确保准确
        )

        threshold = int(incremental_size * threshold_ratio)
        should_skip = pending_count >= threshold

        if should_skip:
            logger.info(
                f"Skipping subscription {subscription_id} update: "
                f"pending={pending_count}, threshold={threshold} "
                f"(ratio={threshold_ratio}, size={incremental_size})",
            )

        return should_skip, pending_count


# 全局单例
queue_monitor = QueueBackpressureMonitor()
