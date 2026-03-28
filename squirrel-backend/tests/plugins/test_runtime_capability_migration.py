import importlib
import importlib.util
import json
from pathlib import Path
import sys
import warnings

import pytest

ROOT = Path(__file__).resolve().parents[3]

for plugin_name in ('bilibili', 'javdb', 'pornhub', 'youtube'):
    sys.path.insert(0, str(ROOT / 'squirrel-plugins' / plugin_name / 'src'))


def _runtime_manifest_capabilities(module_name: str) -> tuple[set[str], set[str]]:
    runtime_module = importlib.import_module(f'{module_name}.runtime')
    runtime = runtime_module.get_plugin_runtime()
    manifest = runtime.manifest()
    capabilities = {item.name for item in manifest.capabilities}
    features = {
        feature
        for site in manifest.sites
        for feature in site.features
    }
    return capabilities, features


def _metadata_capabilities(plugin_name: str) -> tuple[set[str], set[str]]:
    metadata_path = ROOT / 'squirrel-plugins' / plugin_name / 'plugin-runtime.json'
    payload = json.loads(metadata_path.read_text(encoding='utf-8'))
    manifest = payload['manifest']
    capabilities = {item['name'] for item in manifest['capabilities']}
    features = {
        feature
        for site in manifest['sites']
        for feature in site['features']
    }
    return capabilities, features


@pytest.mark.parametrize(
    ('plugin_name', 'module_name', 'expected_capabilities'),
    [
        (
            'bilibili',
            'squirrel_bilibili',
            {'fetch_subtitles', 'build_mpd', 'resolve_proxy_config'},
        ),
        (
            'javdb',
            'squirrel_javdb',
            {'resolve_proxy_config', 'rewrite_proxy_playlist'},
        ),
        (
            'pornhub',
            'squirrel_pornhub',
            {'resolve_proxy_config', 'rewrite_proxy_playlist'},
        ),
        (
            'youtube',
            'squirrel_youtube',
            {'fetch_subtitles', 'build_mpd', 'resolve_proxy_config', 'rewrite_proxy_playlist'},
        ),
    ],
)
def test_runtime_manifests_and_metadata_include_migrated_capabilities(
    plugin_name,
    module_name,
    expected_capabilities,
):
    runtime_capabilities, runtime_features = _runtime_manifest_capabilities(module_name)
    metadata_capabilities, metadata_features = _metadata_capabilities(plugin_name)

    assert expected_capabilities <= runtime_capabilities
    assert expected_capabilities <= runtime_features
    assert expected_capabilities <= metadata_capabilities
    assert expected_capabilities <= metadata_features


def test_bilibili_runtime_media_capabilities_do_not_emit_legacy_registry_warnings(monkeypatch):
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter('always')
        runtime_module = importlib.import_module('squirrel_bilibili.runtime')
        subtitles_module = importlib.import_module('squirrel_bilibili.subtitles')
        mpd_module = importlib.import_module('squirrel_bilibili.mpd')

        monkeypatch.setattr(
            subtitles_module.BilibiliSubtitlesProvider,
            'get_subtitles',
            lambda self, video, lang, fmt='srt': ('subtitle body', 'demo.ai-zh.srt'),
        )
        monkeypatch.setattr(
            mpd_module.BilibiliMpdBuilder,
            'build_mpd',
            lambda self, video: '<MPD></MPD>',
        )

        runtime = runtime_module.get_plugin_runtime()
        subtitles_response = runtime.invoke(
            'fetch_subtitles',
            {
                'video_id': 1,
                'url': 'https://www.bilibili.com/video/BV1xx411c7mD',
                'lang': 'ai-zh',
                'fmt': 'srt',
            },
        )
        mpd_response = runtime.invoke(
            'build_mpd',
            {
                'video_id': 1,
                'url': 'https://www.bilibili.com/video/BV1xx411c7mD',
            },
        )

    assert subtitles_response.ok is True
    assert subtitles_response.data['content'] == 'subtitle body'
    assert subtitles_response.data['filename'] == 'demo.ai-zh.srt'
    assert mpd_response.ok is True
    assert mpd_response.data['content'] == '<MPD></MPD>'
    assert not [item for item in caught if 'legacy' in str(item.message).lower()]


def test_javdb_runtime_proxy_capabilities_do_not_emit_legacy_registry_warnings():
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter('always')
        runtime_module = importlib.import_module('squirrel_javdb.runtime')
        runtime = runtime_module.get_plugin_runtime()

        config_response = runtime.invoke(
            'resolve_proxy_config',
            {
                'domain': 'javdb.com',
            },
        )
        rewrite_response = runtime.invoke(
            'rewrite_proxy_playlist',
            {
                'url': 'https://surrit.com/example/1080p/video.m3u8',
                'content': '#EXTM3U\nsegment-001.ts\n',
                'referer': 'https://missav.ai/en/example-video',
            },
        )

    assert config_response.ok is True
    assert config_response.data['site_headers']['Referer'] == 'https://javdb.com/'
    assert config_response.data['domain_configs'][0]['domain'] == 'javdb.com'
    assert rewrite_response.ok is True
    assert '/api/video/proxy?domain=javdb.com' in rewrite_response.data['content']
    assert 'referer=https%3A%2F%2Fmissav.ai%2Fen%2Fexample-video' in rewrite_response.data['content']
    assert not [item for item in caught if 'legacy' in str(item.message).lower()]


@pytest.mark.parametrize(
    ('module_name', 'plugin_name', 'video_url'),
    [
        ('squirrel_bilibili', 'bilibili', 'https://www.bilibili.com/video/BV1xx411c7mD'),
        ('squirrel_javdb', 'javdb', 'https://javdb.com/v/test-video'),
        ('squirrel_pornhub', 'pornhub', 'https://www.pornhub.com/view_video.php?viewkey=ph-test'),
    ],
)
def test_runtime_plugins_no_longer_ship_downloader_modules(module_name, plugin_name, video_url, monkeypatch):
    assert importlib.util.find_spec(f'{module_name}.downloader') is None

    if plugin_name != 'javdb':
        return

    runtime_module = importlib.import_module(f'{module_name}.runtime')
    html_client = importlib.import_module(f'{module_name}.html_client')

    class _Response:
        text = '''
        <html>
          <div class="title"><strong>ABP-123</strong><strong>Demo Title</strong></div>
          <img class="video-cover" src="/images/demo.jpg" />
          <div class="movie-panel-info">
            <div class="panel-block"><span>ignore</span></div>
            <div class="panel-block"><span>2026-03-28</span></div>
            <div class="panel-block"><span>120 分鍾</span></div>
          </div>
        </html>
        '''

    monkeypatch.setattr(html_client, 'fetch_javdb_html', lambda *args, **kwargs: _Response())

    runtime = runtime_module.get_plugin_runtime()
    response = runtime.invoke('extract_video', {'url': video_url})

    assert response.ok is True
    assert response.data['success'] is True
    assert response.data['data']['title'] == 'ABP-123 Demo Title'


@pytest.mark.parametrize(
    'module_name',
    ['squirrel_bilibili', 'squirrel_javdb', 'squirrel_pornhub', 'squirrel_youtube'],
)
def test_runtime_plugins_no_longer_ship_config_modules(module_name):
    assert importlib.util.find_spec(f'{module_name}.config') is None
