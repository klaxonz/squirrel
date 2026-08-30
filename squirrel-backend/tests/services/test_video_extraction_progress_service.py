from domains.video.application.services.extraction.progress_service import VideoExtractionProgressService
from domains.video.interfaces.dto.video_dto import VideoExtractDto


def _params():
    return VideoExtractDto(
        url='https://www.youtube.com/watch?v=demo',
        subscribed=True,
        only_extract=True,
        subscription_id=1,
        sync_state_id=2,
        run_id='run-1',
        trigger='scheduled',
        is_manual=False,
        is_extract_all=False,
    )


def test_record_terminal_completes_pending_on_success():
    decrement_calls = []
    lifecycle = type(
        'Lifecycle',
        (),
        {'record_video_extraction_terminal': lambda self, *args, **kwargs: decrement_calls.append((args, kwargs))},
    )()

    VideoExtractionProgressService(lifecycle).record_terminal(_params(), succeeded=True)

    assert decrement_calls == [
        (
            (2,),
            {
                'succeeded': True,
                'run_id': 'run-1',
            },
        ),
    ]


def test_record_terminal_updates_pending_on_failure():
    decrement_calls = []
    lifecycle = type(
        'Lifecycle',
        (),
        {'record_video_extraction_terminal': lambda self, *args, **kwargs: decrement_calls.append((args, kwargs))},
    )()

    VideoExtractionProgressService(lifecycle).record_terminal(_params(), succeeded=False)

    assert decrement_calls == [
        (
            (2,),
            {
                'succeeded': False,
                'run_id': 'run-1',
            },
        ),
    ]
