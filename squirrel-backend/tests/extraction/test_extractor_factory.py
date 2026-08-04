import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from sites.crawl import ExtractionResult, VideoMeta

import infrastructure.extraction.factory as factory_module
from infrastructure.extraction.contracts import ExtractionTask
from infrastructure.extraction.factory import ExtractorFactory


def test_site_extractor_adapter_extracts_via_site(monkeypatch):
    calls = []

    class _FakeSite:
        def extract_video(self, url):
            calls.append(('extract_video', url))
            return ExtractionResult.success_result(
                VideoMeta(
                    title='Test video',
                    url='https://www.bilibili.com/video/BV1xx411c7mD',
                    thumbnail='https://img.example.com/video.jpg',
                    duration=120,
                    publish_date=None,
                    extra_data={'id': 'BV1xx411c7mD'},
                )
            )

    class _FakeRegistry:
        def has_capability(self, site_name, capability):
            return capability == 'extract_video' and site_name == 'bilibili'

        def get_site_runtime(self, site_name):
            calls.append(('load', site_name))
            return _FakeSite()

    monkeypatch.setattr(
        'infrastructure.extraction.factory.SiteCatalog.is_site_enabled',
        lambda site=None, domain=None: True,
    )
    monkeypatch.setattr(
        'infrastructure.extraction.factory.SiteCatalog.find_site_by_domain',
        lambda domain: ('bilibili', {'domains': ['bilibili.com', 'b23.tv']}),
    )
    monkeypatch.setattr(
        'infrastructure.extraction.factory.get_effective_site_catalog',
        lambda: {
            'bilibili': {
                'domains': ['bilibili.com', 'b23.tv'],
                'test_url': 'https://www.bilibili.com',
                'enabled': True,
            },
        },
    )

    factory = ExtractorFactory(registry=_FakeRegistry())
    extractor = factory.create_extractor('https://www.bilibili.com/video/BV1xx411c7mD')

    assert extractor is not None

    result = extractor.extract(
        ExtractionTask(
            url='https://www.bilibili.com/video/BV1xx411c7mD',
            site_name='bilibili',
            metadata={'source': 'test'},
        ),
    )

    assert len(calls) == 2
    assert calls[0] == ('load', 'bilibili')
    assert calls[1] == ('extract_video', 'https://www.bilibili.com/video/BV1xx411c7mD')
    assert result.success is True
    assert result.data is not None
    assert result.data.title == 'Test video'


def test_get_extractor_factory_initializes_without_legacy_registry(monkeypatch):
    factory_module.reset_factory()

    monkeypatch.setattr(
        'infrastructure.extraction.factory.SiteCatalog.get_catalog',
        dict,
    )

    factory = factory_module.get_extractor_factory()

    assert isinstance(factory, ExtractorFactory)
    assert factory is factory_module.get_extractor_factory()
