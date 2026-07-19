from __future__ import annotations

from domains.subscription.application.services.core.import_service import process_import_payload
from domains.subscription.domain.models.crawl_task import CrawlTask


def execute_subscription_import_task(task: CrawlTask):
    return process_import_payload(task.payload or {})
