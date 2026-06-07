import asyncio
import logging

from schedule.task import BaseTask, TaskRegistry
from utils.cloudflare_bypass import get_default_client

logger = logging.getLogger(__name__)


@TaskRegistry.register(interval=2, unit="minutes", start_immediately=True)
class CloudflareHeartbeatTask(BaseTask):

    @classmethod
    def run(cls):
        try:
            client = get_default_client()
            asyncio.run(client.health())
            logger.info("CloudflareHeartbeatTask health check passed")
        except Exception as e:  # task boundary -- prevent single failure from crashing scheduler
            logger.error(f"CloudflareHeartbeatTask error: {e}", exc_info=True)

    @classmethod
    def shutdown(cls):
        logger.info("CloudflareHeartbeatTask shutdown")
