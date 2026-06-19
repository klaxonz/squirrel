import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from infrastructure.extraction.contracts import ExtractionTask
from infrastructure.extraction.exceptions import ExtractionError, VipError
from infrastructure.extraction.pipeline.context import PipelineContext
from infrastructure.extraction.pipeline.stages.extraction import ExtractionStage


def _build_context(url: str) -> PipelineContext:
    return PipelineContext(
        task=ExtractionTask(
            url=url,
            site_name='pornhub',
            metadata={},
        ),
    )


def test_extraction_stage_records_blocked_video_for_short_redirect(monkeypatch):
    calls = []
    monkeypatch.setattr(
        'infrastructure.extraction.pipeline.stages.extraction.record_blocked_video',
        lambda **kwargs: calls.append(kwargs),
    )

    stage = ExtractionStage(extractor_factory=None)
    context = _build_context('https://www.pornhub.com/view_video.php?viewkey=698e147975244')
    error = ExtractionError(
        'unsupported short video',
        context={'blocked_reason_code': 'unsupported_short_redirect'},
    )

    stage.on_error(context, error)

    assert calls == [
        {
            'url': 'https://www.pornhub.com/view_video.php?viewkey=698e147975244',
            'reason_code': 'unsupported_short_redirect',
            'error_message': str(error),
            'error_type': 'ExtractionError',
        }
    ]


def test_extraction_stage_records_blocked_video_for_vip(monkeypatch):
    calls = []
    monkeypatch.setattr(
        'infrastructure.extraction.pipeline.stages.extraction.record_blocked_video',
        lambda **kwargs: calls.append(kwargs),
    )

    stage = ExtractionStage(extractor_factory=None)
    context = _build_context('https://www.pornhub.com/view_video.php?viewkey=vip-demo')
    error = VipError('vip required')

    stage.on_error(context, error)

    assert calls == [
        {
            'url': 'https://www.pornhub.com/view_video.php?viewkey=vip-demo',
            'reason_code': 'vip_required',
            'error_message': str(error),
            'error_type': 'VipError',
        }
    ]
