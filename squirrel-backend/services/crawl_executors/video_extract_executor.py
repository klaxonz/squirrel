from __future__ import annotations

from models.crawl_task import CrawlTask
from schemas.video.dto.video_dto import VideoExtractDto
from services.video_extraction import extract_video


class CrawlExecutorService:
    @staticmethod
    def execute_video_extract_payload(payload: dict):
        params = VideoExtractDto.model_validate(payload)
        result = extract_video(params)
        if not result.success:
            raise ValueError(result.error or "video_extract_failed")
        return result

    @staticmethod
    def execute_video_extract_task(task: CrawlTask):
        return CrawlExecutorService.execute_video_extract_payload(task.payload or {})


_default = CrawlExecutorService()
execute_video_extract_payload = _default.execute_video_extract_payload
execute_video_extract_task = _default.execute_video_extract_task
