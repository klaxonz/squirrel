import logging
from schedule.task import TaskRegistry, BaseTask
from utils.cloudflare_bypass import get_default_client

logger = logging.getLogger(__name__)


@TaskRegistry.register(interval=5, unit='minutes', start_immediately=False)
class CloudflareHeartbeatTask(BaseTask):

    @classmethod
    def run(cls):
        try:
            client = get_default_client()
            test_url = "https://www.youtube.com"

            result = client.fetch(url=test_url, follow_redirects=False)

            if result.success:
                logger.debug(f"Cloudflare heartbeat success: {result.elapsed:.2f}s")
            else:
                logger.warning(f"Cloudflare heartbeat failed: {result.error}")

        except Exception as e:
            logger.error(f"CloudflareHeartbeatTask error: {e}", exc_info=True)

    @classmethod
    def shutdown(cls):
        logger.info("CloudflareHeartbeatTask shutdown")
