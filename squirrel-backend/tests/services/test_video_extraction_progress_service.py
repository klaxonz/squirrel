from domains.video.application.services.extraction.progress_service import VideoExtractionProgressService
from domains.video.interfaces.dto.dto.video_dto import VideoExtractDto


def _params():
    return VideoExtractDto(
        url="https://www.youtube.com/watch?v=demo",
        subscribed=True,
        only_extract=True,
        subscription_id=1,
        sync_state_id=2,
        run_id="run-1",
        trigger="scheduled",
        is_manual=False,
        is_extract_all=False,
    )


def test_record_finished_clears_dedupe_and_completes_pending_on_success(monkeypatch):
    events = []
    clear_calls = []
    decrement_calls = []

    monkeypatch.setattr(
        "services.video.extraction.progress_service.append_event",
        lambda event: events.append(event),
    )
    monkeypatch.setattr(
        "services.video.extraction.progress_service.video_extraction_task_service.clear_video_extraction_dedupe",
        lambda params: clear_calls.append(params.url),
    )
    monkeypatch.setattr(
        "services.video.extraction.progress_service.subscription_sync_state_service.decrement_pending_video_count",
        lambda *args, **kwargs: decrement_calls.append((args, kwargs)),
    )

    VideoExtractionProgressService().record_finished(_params(), succeeded=True, site="youtube.com")

    assert [event.event_type for event in events] == ["video_extracted"]
    assert clear_calls == ["https://www.youtube.com/watch?v=demo"]
    assert decrement_calls == [
        (
            (2,),
            {
                "run_id": "run-1",
                "trigger": "scheduled",
                "allow_completion": True,
            },
        ),
    ]


def test_record_finished_clears_dedupe_without_completing_pending_on_failure(monkeypatch):
    events = []
    clear_calls = []
    decrement_calls = []

    monkeypatch.setattr(
        "services.video.extraction.progress_service.append_event",
        lambda event: events.append(event),
    )
    monkeypatch.setattr(
        "services.video.extraction.progress_service.video_extraction_task_service.clear_video_extraction_dedupe",
        lambda params: clear_calls.append(params.url),
    )
    monkeypatch.setattr(
        "services.video.extraction.progress_service.subscription_sync_state_service.decrement_pending_video_count",
        lambda *args, **kwargs: decrement_calls.append((args, kwargs)),
    )

    VideoExtractionProgressService().record_finished(_params(), succeeded=False, site="youtube.com")

    assert events == []
    assert clear_calls == ["https://www.youtube.com/watch?v=demo"]
    assert decrement_calls == [
        (
            (2,),
            {
                "run_id": "run-1",
                "trigger": "scheduled",
                "allow_completion": False,
            },
        ),
    ]
