from __future__ import annotations

from domains.subscription.application.services.crawl.tasks.errors import CrawlExecutionError
from domains.subscription.domain.models.crawl_task import CrawlTask
from domains.video.application.services.extraction.extractor import VideoExtractionService
from domains.video.interfaces.dto.video_dto import VideoExtractDto


class CrawlExecutorService:
    def __init__(self, extraction_service: VideoExtractionService):
        self._extraction_service = extraction_service

    def execute_video_extract_payload(self, payload: dict):
        params = VideoExtractDto.model_validate(payload)
        result = self._extraction_service.extract_video(params)
        if not result.success:
            raise CrawlExecutionError(
                result.error or 'video_extract_failed',
                retryable=bool(getattr(result, 'retryable', False)),
                error_type=getattr(result, 'error_category', None) or 'video_extract_failed',
            )
        return result

    def execute_video_extract_task(self, task: CrawlTask):
        return self.execute_video_extract_payload(
            {
                **(task.payload or {}),
                'crawl_task_id': task.id,
                'execution_token': task.lease_token,
            },
        )
