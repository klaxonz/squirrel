from datetime import datetime
from pathlib import Path
import sys
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from core.extraction.contracts import ExtractionTask
from core.extraction.dto import VideoDTO
from core.extraction.pipeline.context import PipelineContext
from core.extraction.pipeline.stages.post_process import PostProcessStage


class _RecordingThumbnailService:
    def __init__(self):
        self.calls = []

    def enqueue_download(self, video_id, thumbnail_url, site_name):
        self.calls.append((video_id, thumbnail_url, site_name))

def test_post_process_stage_keeps_thumbnail_work_but_skips_download_task_creation():
    thumbnail_service = _RecordingThumbnailService()
    stage = PostProcessStage(thumbnail_service)
    context = PipelineContext(
        task=ExtractionTask(
            url='https://www.youtube.com/watch?v=demo',
            site_name='youtube',
            metadata={'only_extract': False},
        ),
        video_model=SimpleNamespace(id=42),
        video_dto=VideoDTO(
            url='https://www.youtube.com/watch?v=demo',
            title='Runtime video',
            site_name='youtube',
            thumbnail='https://img.example.com/thumb.jpg',
            publish_date=datetime(2024, 1, 1),
        ),
    )

    result = stage.execute(context)

    assert result is context
    assert thumbnail_service.calls == [(42, 'https://img.example.com/thumb.jpg', 'youtube')]
