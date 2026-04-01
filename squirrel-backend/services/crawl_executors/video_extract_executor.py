from __future__ import annotations

from models.crawl_task import CrawlTask
from schemas.video.dto.video_dto import VideoExtractDto
from services.video_extraction import extract_video


def execute_video_extract_payload(payload: dict):
    params = VideoExtractDto.model_validate(payload)
    return extract_video(params)


def execute_video_extract_task(task: CrawlTask):
    return execute_video_extract_payload(task.payload or {})
