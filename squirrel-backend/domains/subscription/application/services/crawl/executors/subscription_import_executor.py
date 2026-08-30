from __future__ import annotations

from domains.subscription.application.services.core.import_service import SubscriptionImportService
from domains.subscription.domain.models.crawl_task import CrawlTask


class SubscriptionImportExecutor:
    def __init__(self, import_service: SubscriptionImportService):
        self._import_service = import_service

    def execute_subscription_import_task(self, task: CrawlTask):
        return self._import_service.process_import_payload(task.payload or {})
