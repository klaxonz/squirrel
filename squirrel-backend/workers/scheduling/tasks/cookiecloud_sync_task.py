import logging

from infrastructure.scheduling.base import BaseTask, TaskRegistry
from infrastructure.site_catalog.cookiecloud import sync_cookiecloud_to_site_files

logger = logging.getLogger(__name__)


@TaskRegistry.register(interval=60 * 5, unit="minutes", start_immediately=False)
class CookieCloudSyncTask(BaseTask):
    interval = 60 * 5
    unit = "minutes"
    start_immediately = False

    @classmethod
    def run(cls):
        logger.info("[CookieCloudSyncTask] Start syncing cookies from CookieCloud")
        result = sync_cookiecloud_to_site_files()
        logger.info(
            "[CookieCloudSyncTask] Sync finished, updated_sites=%s, total_cookie_entries=%s",
            result.get("updated_sites"),
            result.get("total_cookie_entries"),
        )
        return result
