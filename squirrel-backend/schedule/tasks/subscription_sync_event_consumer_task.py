import logging

from schedule.task import BaseTask, TaskRegistry
from services import outbox_event_service

logger = logging.getLogger(__name__)


@TaskRegistry.register(interval=15, unit="seconds", start_immediately=True)
class SubscriptionSyncEventConsumerTask(BaseTask):
    """Consume pending subscription sync outbox events."""

    @classmethod
    def run(cls):
        try:
            summary = outbox_event_service.consume_available_events(limit=50)
            logger.info("Subscription sync outbox consumer processed=%s failed=%s", summary["processed"], summary["failed"])
        except Exception as exc:  # task boundary -- prevent single failure from crashing scheduler
            logger.error("SubscriptionSyncEventConsumerTask.run error: %s", exc, exc_info=True)

    @classmethod
    def shutdown(cls):
        logger.info("SubscriptionSyncEventConsumerTask task shutdown")
