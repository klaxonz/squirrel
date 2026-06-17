from __future__ import annotations

from collections.abc import Callable

from domains.subscription.domain.models.crawl_task import CrawlTask
from domains.video.application.services.extraction.extractor import extract_video
from domains.video.interfaces.dto.video_dto import VideoExtractDto


class CrawlExecutorService:
    def __init__(
        self,
        session_factory=None,
        get_type_mapping: Callable[[str], object] | None = None,
        extract_video_func: Callable | None = None,
    ):
        self.session_factory = session_factory
        self.get_type_mapping = get_type_mapping
        self._extract_video = extract_video_func or extract_video

    def execute_video_extract_payload(self, payload: dict):
        params = VideoExtractDto.model_validate(payload)
        result = self._extract_video(params)
        if not result.success:
            raise ValueError(result.error or "video_extract_failed")
        return result

    def execute_video_extract_task(self, task: CrawlTask):
        return self.execute_video_extract_payload(task.payload or {})


video_extract_executor = CrawlExecutorService()
execute_video_extract_payload = video_extract_executor.execute_video_extract_payload
execute_video_extract_task = video_extract_executor.execute_video_extract_task
