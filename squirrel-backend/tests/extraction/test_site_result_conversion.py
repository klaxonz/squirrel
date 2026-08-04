"""Tests for the site result -> pipeline result conversion boundary."""

import pytest

from sites.crawl import AuthError, ExtractionResult, VideoMeta

from infrastructure.extraction.contracts import site_result_to_extraction_result
from infrastructure.extraction.runtime_payloads import RuntimeVideoData


def _video_meta():
    return VideoMeta(
        title='Demo',
        url='https://www.bilibili.com/video/BV1xx411c7mD',
        thumbnail='https://img.example.com/v.jpg',
        duration=120,
        publish_date='2026-03-29T15:39:03',
        extra_data={'id': 'BV1xx411c7mD', 'owner': {'name': 'demo'}},
    )


def test_success_conversion_maps_video_meta_to_runtime_video_data_losslessly():
    site_result = ExtractionResult.success_result(_video_meta())

    pipeline_result = site_result_to_extraction_result(site_result)

    assert pipeline_result.success is True
    assert isinstance(pipeline_result.data, RuntimeVideoData)
    assert pipeline_result.data.title == 'Demo'
    assert pipeline_result.data.url == 'https://www.bilibili.com/video/BV1xx411c7mD'
    assert pipeline_result.data.thumbnail == 'https://img.example.com/v.jpg'
    assert pipeline_result.data.duration == 120
    assert pipeline_result.data.publish_date == '2026-03-29T15:39:03'
    assert pipeline_result.data.extra_data == {'id': 'BV1xx411c7mD', 'owner': {'name': 'demo'}}


def test_failure_conversion_preserves_error_fields_exactly():
    site_result = ExtractionResult(
        success=False,
        error='login required',
        error_category='auth',
        retryable=True,
        error_context={'url': 'https://www.bilibili.com/video/BV1xx411c7mD', 'code': -101},
    )

    pipeline_result = site_result_to_extraction_result(site_result)

    assert pipeline_result.success is False
    assert pipeline_result.error == 'login required'
    assert pipeline_result.error_category == 'auth'
    assert pipeline_result.retryable is True
    assert pipeline_result.error_context == {'url': 'https://www.bilibili.com/video/BV1xx411c7mD', 'code': -101}
    assert pipeline_result.data is None


def test_failure_conversion_preserves_none_context_as_none():
    site_result = ExtractionResult(success=False, error='site_disabled')

    pipeline_result = site_result_to_extraction_result(site_result)

    assert pipeline_result.error == 'site_disabled'
    assert pipeline_result.error_context is None
    assert pipeline_result.retryable is False


def test_success_conversion_rejects_non_video_meta_data():
    site_result = ExtractionResult(success=True, data='not a video meta')

    with pytest.raises(TypeError, match='must carry VideoMeta'):
        site_result_to_extraction_result(site_result)


def test_success_conversion_rejects_none_data():
    site_result = ExtractionResult(success=True, data=None)

    with pytest.raises(TypeError, match='must carry VideoMeta'):
        site_result_to_extraction_result(site_result)


def test_adapter_round_trip_keeps_site_error_semantics():
    site_result = ExtractionResult(
        success=False,
        error=str(AuthError('login required')),
        error_category='auth',
        retryable=False,
        error_context={'url': 'https://www.bilibili.com/video/BV1xx411c7mD'},
    )

    pipeline_result = site_result_to_extraction_result(site_result)

    assert pipeline_result.error_category == 'auth'
    assert pipeline_result.retryable is False
