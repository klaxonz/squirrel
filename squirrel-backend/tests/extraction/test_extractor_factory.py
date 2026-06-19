import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import infrastructure.extraction.factory as factory_module
from infrastructure.extraction.contracts import ExtractionTask
from infrastructure.extraction.factory import ExtractorFactory
from infrastructure.site_plugins.registry import SitePluginResult


def test_plugin_extractor_adapter_extracts_via_site_plugin(monkeypatch):
    calls = []

    class _FakeRegistry:
        def has_capability(self, site_name, capability):
            return capability == 'extract_video' and site_name == 'bilibili'

        def invoke(self, capability, payload=None, site_name=None, domain=None):
            calls.append(
                {
                    'capability': capability,
                    'payload': payload,
                    'site_name': site_name,
                    'domain': domain,
                }
            )
            return SitePluginResult(
                ok=True,
                data={
                    'success': True,
                    'data': {
                        'title': 'Test video',
                        'url': 'https://www.bilibili.com/video/BV1xx411c7mD',
                        'thumbnail': 'https://img.example.com/video.jpg',
                        'duration': 120,
                        'publish_date': None,
                        'extra_data': {'id': 'BV1xx411c7mD'},
                    },
                },
            )

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

    factory = ExtractorFactory(plugin_registry=_FakeRegistry())
    extractor = factory.create_extractor('https://www.bilibili.com/video/BV1xx411c7mD')

    assert extractor is not None

    result = extractor.extract(
        ExtractionTask(
            url='https://www.bilibili.com/video/BV1xx411c7mD',
            site_name='bilibili',
            metadata={'source': 'test'},
        ),
    )

    assert len(calls) == 1
    assert calls[0]['capability'] == 'extract_video'
    assert calls[0]['site_name'] == 'bilibili'
    assert calls[0]['domain'] is None
    assert calls[0]['payload']['url'] == 'https://www.bilibili.com/video/BV1xx411c7mD'
    assert calls[0]['payload']['site_name'] == 'bilibili'
    assert calls[0]['payload']['retry_count'] == 0
    assert calls[0]['payload']['max_retries'] == 3
    assert calls[0]['payload']['metadata'] == {'source': 'test'}
    assert calls[0]['payload']['task_id']
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
