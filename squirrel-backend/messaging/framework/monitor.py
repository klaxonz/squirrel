import logging
from typing import Any

logger = logging.getLogger(__name__)


class QueueBackpressureMonitor:
    """Queue backpressure monitor"""

    def __init__(self, crawl_task_service: Any = None):
        self._crawl_task_service = crawl_task_service

    def _get_crawl_task_service(self):
        if self._crawl_task_service is None:
            from services.crawl.tasks import service as crawl_task_service
            self._crawl_task_service = crawl_task_service
        return self._crawl_task_service

    def count_pending_videos_for_subscription(
        self,
        subscription_id: int,
        url: str,
        check_limit: int = 1000,
    ) -> int:
        """Count the number of pending videos for a subscription in the video extraction queue

        Args:
            subscription_id: Subscription ID
            url: Subscription URL (used to determine the queue)
            check_limit: Maximum number of recent messages to check in the queue (avoids full scan)

        Returns:
            Number of pending videos

        """
        try:
            return self._get_crawl_task_service().count_pending_video_tasks_for_subscription(subscription_id)
        except (ConnectionError, OSError, ValueError, TypeError) as e:
            logger.error("Failed to count pending videos for subscription %s: %s", subscription_id, e)
            return 0

    def should_skip_subscription_update(
        self,
        subscription_id: int,
        url: str,
        threshold_ratio: float = 0.5,
        incremental_size: int = 30,
    ) -> tuple[bool, int | None]:
        """Determine whether to skip this subscription update

        Args:
            subscription_id: Subscription ID
            url: Subscription URL
            threshold_ratio: Threshold ratio (default 0.5, i.e. more than half)
            incremental_size: Incremental update size (default 30)

        Returns:
            (whether to skip, count in queue)

        """
        pending_count = self.count_pending_videos_for_subscription(
            subscription_id,
            url,
            check_limit=incremental_size * 2,  # Check 2x the count for accuracy
        )

        threshold = int(incremental_size * threshold_ratio)
        should_skip = pending_count >= threshold

        if should_skip:
            logger.info("Skipping subscription %s update: pending=%s, threshold=%s (ratio=%s, size=%s)", subscription_id, pending_count, threshold, threshold_ratio, incremental_size)

        return should_skip, pending_count


