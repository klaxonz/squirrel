from domains.subscription.application.services.core.sync.lifecycle import SubscriptionSyncLifecycle
from domains.video.interfaces.dto.video_dto import VideoExtractDto


class VideoExtractionProgressService:
    def __init__(self, lifecycle: SubscriptionSyncLifecycle):
        self._lifecycle = lifecycle

    def record_terminal(self, params: VideoExtractDto, *, succeeded: bool) -> None:
        self._lifecycle.record_video_extraction_terminal(
            params.sync_state_id,
            succeeded=succeeded,
            run_id=params.run_id,
        )
