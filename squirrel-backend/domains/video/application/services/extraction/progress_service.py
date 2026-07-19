from domains.subscription.application.services.core.sync.lifecycle import subscription_sync_lifecycle
from domains.video.interfaces.dto.video_dto import VideoExtractDto


class VideoExtractionProgressService:
    def record_terminal(self, params: VideoExtractDto, *, succeeded: bool) -> None:
        subscription_sync_lifecycle.record_video_extraction_terminal(
            params.sync_state_id,
            succeeded=succeeded,
            run_id=params.run_id,
        )


video_extraction_progress_service = VideoExtractionProgressService()
record_terminal = video_extraction_progress_service.record_terminal
