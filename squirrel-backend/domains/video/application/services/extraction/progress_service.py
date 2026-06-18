import domains.subscription.application.services.core.sync.state.service as subscription_sync_state_service
import domains.video.application.services.extraction.task_service as video_extraction_task_service
from domains.video.interfaces.dto.video_dto import VideoExtractDto


class VideoExtractionProgressService:
    def record_finished(self, params: VideoExtractDto, *, succeeded: bool, site: str) -> None:
        video_extraction_task_service.clear_video_extraction_dedupe(params)
        subscription_sync_state_service.decrement_pending_video_count(
            params.sync_state_id,
            allow_completion=succeeded,
        )


video_extraction_progress_service = VideoExtractionProgressService()
record_finished = video_extraction_progress_service.record_finished
