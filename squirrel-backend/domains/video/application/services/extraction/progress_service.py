import domains.subscription.application.services.core.sync.state.service as subscription_sync_state_service
import domains.video.application.services.extraction.task_service as video_extraction_task_service
from domains.subscription.application.services.core.sync.event_service import SyncEventInput, append_event
from domains.subscription.application.services.core.sync.run_service import SyncEventType, SyncRunStatus
from domains.video.interfaces.dto.dto.video_dto import VideoExtractDto


class VideoExtractionProgressService:
    def record_finished(self, params: VideoExtractDto, *, succeeded: bool, site: str) -> None:
        if succeeded and params.run_id:
            append_event(
                SyncEventInput(
                    stream_id=params.run_id,
                    subscription_id=params.subscription_id,
                    sync_state_id=params.sync_state_id,
                    site=site,
                    sync_mode="full" if params.is_extract_all else "incremental",
                    trigger=params.trigger or ("manual" if params.is_manual else "scheduled"),
                    event_type=SyncEventType.VIDEO_EXTRACTED,
                    event_phase="extracting",
                    event_status=SyncRunStatus.RUNNING,
                    payload={"videos_extracted_delta": 1, "video_url": params.url},
                ),
            )

        video_extraction_task_service.clear_video_extraction_dedupe(params)
        subscription_sync_state_service.decrement_pending_video_count(
            params.sync_state_id,
            run_id=params.run_id,
            trigger=params.trigger or ("manual" if params.is_manual else "scheduled"),
            allow_completion=succeeded,
        )


video_extraction_progress_service = VideoExtractionProgressService()
record_finished = video_extraction_progress_service.record_finished
