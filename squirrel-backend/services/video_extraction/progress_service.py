from schemas.video.dto.video_dto import VideoExtractDto
from services import subscription_sync_state_service
from services.subscription_sync_event_service import SyncEventInput, append_event
from services.subscription_sync_run_service import SyncEventType, SyncRunStatus
from services.video_extraction import task_service as video_extraction_task_service


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


_default = VideoExtractionProgressService()
record_finished = _default.record_finished
