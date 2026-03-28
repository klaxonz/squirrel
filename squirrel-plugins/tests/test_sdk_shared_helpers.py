from __future__ import annotations

import importlib
import sys
import types
import unittest
from contextlib import contextmanager
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SDK_CRAWL_ROOT = REPO_ROOT / 'squirrel-sdk' / 'src' / 'crawl'


@contextmanager
def _stub_sdk_crawl_package():
    originals = {
        name: module
        for name, module in sys.modules.items()
        if name == 'crawl' or name.startswith('crawl.')
    }
    package_module = types.ModuleType('crawl')
    package_module.__path__ = [str(SDK_CRAWL_ROOT)]

    try:
        for name in list(originals):
            sys.modules.pop(name, None)
        sys.modules['crawl'] = package_module
        yield
    finally:
        for name in list(sys.modules):
            if name == 'crawl' or name.startswith('crawl.'):
                sys.modules.pop(name, None)
        sys.modules.update(originals)


class _Dictable:
    def __init__(self, payload):
        self._payload = payload

    def to_dict(self):
        return dict(self._payload)


class _FakeImporter:
    def get_user_subscriptions(self):
        return [
            _Dictable({'url': 'https://example.com/one'}),
            _Dictable({'url': 'https://example.com/two'}),
        ]


class _FakeSubscription:
    def __init__(self, url: str) -> None:
        self.url = url

    def get_subscribe_info(self):
        return _Dictable({
            'id': 'channel-1',
            'name': 'Demo Channel',
            'avatar': 'https://cdn.example/avatar.jpg',
            'url': self.url,
        })

    def sync_videos(self, context):
        return _Dictable({
            'video_urls': ['https://example.com/watch?v=latest'],
            'latest_video_url': 'https://example.com/watch?v=latest',
            'cursor_payload': {'latest_video_url': 'https://example.com/watch?v=latest'},
            'stop_reason': 'source_exhausted',
            'total_available': 1,
            'mode': context.mode,
        })


class _FakeExtractor:
    def extract(self, task):
        return _Dictable({
            'success': True,
            'url': task.url,
            'site_name': task.site_name,
        })


class _FakePlaybackHandler:
    def get_video_url(self, video):
        return {
            'video_id': video.id,
            'url': video.url,
            'title': video.title,
        }


class _FakeSubtitlesProvider:
    def get_subtitles(self, _video, lang, fmt):
        return f'subtitles:{lang}:{fmt}', f'demo.{fmt}'


class _FakeMpdBuilder:
    def build_mpd(self, _video):
        return '<MPD />'


class SharedSdkHelperTests(unittest.TestCase):
    def test_plugin_runtime_wraps_generic_handler_exceptions(self):
        with _stub_sdk_crawl_package():
            plugin_module = importlib.import_module('crawl.plugin')
            runtime_models = importlib.import_module('crawl.runtime_models')
            runtime_errors = importlib.import_module('crawl.runtime_errors')

        manifest = runtime_models.PluginManifest(
            plugin_id='demo',
            version='0.1.0',
            display_name='Demo',
            capabilities=[],
            sites=[],
            permissions=[],
        )
        runtime = plugin_module.create_plugin_runtime(
            manifest=manifest,
            capability_handlers={
                'resolve_playback': lambda _payload: (_ for _ in ()).throw(RuntimeError('boom')),
            },
        )

        response = runtime.invoke('resolve_playback', {'request_id': 'req-1'})

        self.assertFalse(response.ok)
        self.assertEqual(response.request_id, 'req-1')
        self.assertIsNotNone(response.error)
        self.assertEqual(response.error.code, runtime_errors.RuntimeErrorCode.CRASHED)
        self.assertEqual(response.error.message, 'boom')
        self.assertEqual(response.error.details, {'exception_type': 'RuntimeError'})

    def test_playlist_rewrite_helper_rewrites_media_lines_and_uri_attributes(self):
        with _stub_sdk_crawl_package():
            module = importlib.import_module('crawl.playlist_rewrite')

        rewritten = module.rewrite_playlist_for_proxy(
            url='https://cdn.example.com/path/master.m3u8',
            content='#EXTM3U\n#EXT-X-MAP:URI="init.mp4"\n# comment teaser.ts\nsegment-1.ts\n',
            site_domain='example.com',
            referer='https://www.example.com/watch',
        )['content']

        lines = rewritten.splitlines()
        self.assertIn('URI="/api/video/proxy?', lines[1])
        self.assertEqual(lines[2], '# comment teaser.ts')
        self.assertTrue(lines[3].startswith('/api/video/proxy?'))

    def test_subscription_helpers_deduplicate_urls_and_build_cursor_payload(self):
        with _stub_sdk_crawl_package():
            module = importlib.import_module('crawl.subscription_helpers')
            core_module = importlib.import_module('crawl.core')

        context = core_module.SubscriptionSyncContext(
            mode='incremental',
            cursor_payload={'page': 1},
            last_seen_video_url='https://example.com/watch?v=seen',
            limit=5,
        )
        limit = module.resolve_subscription_limit(context)
        video_urls: list[str] = []
        seen_urls: set[str] = set()
        latest_video_url = None

        latest_video_url, stop_reason = module.append_subscription_video_url(
            'https://example.com/watch?v=new',
            video_urls=video_urls,
            seen_urls=seen_urls,
            context=context,
            latest_video_url=latest_video_url,
            limit=limit,
        )
        self.assertIsNone(stop_reason)

        latest_video_url, stop_reason = module.append_subscription_video_url(
            'https://example.com/watch?v=new',
            video_urls=video_urls,
            seen_urls=seen_urls,
            context=context,
            latest_video_url=latest_video_url,
            limit=limit,
        )
        self.assertIsNone(stop_reason)

        latest_video_url, stop_reason = module.append_subscription_video_url(
            'https://example.com/watch?v=seen',
            video_urls=video_urls,
            seen_urls=seen_urls,
            context=context,
            latest_video_url=latest_video_url,
            limit=limit,
        )

        self.assertEqual(video_urls, ['https://example.com/watch?v=new'])
        self.assertEqual(latest_video_url, 'https://example.com/watch?v=new')
        self.assertEqual(stop_reason, 'cursor_hit')

        result = module.build_subscription_sync_result(
            video_urls=video_urls,
            latest_video_url=latest_video_url,
            context=context,
            stop_reason=stop_reason,
        )
        self.assertEqual(result.cursor_payload, {'latest_video_url': 'https://example.com/watch?v=new'})
        self.assertEqual(result.total_available, 1)

    def test_runtime_helper_builds_common_runtime_handlers(self):
        with _stub_sdk_crawl_package():
            module = importlib.import_module('crawl.runtime_helpers')
            runtime_models = importlib.import_module('crawl.runtime_models')

        manifest = runtime_models.PluginManifest(
            plugin_id='demo',
            version='0.1.0',
            display_name='Demo',
            capabilities=[],
            sites=[],
            permissions=[],
        )

        runtime = module.create_site_runtime(
            manifest=manifest,
            health_message='Demo runtime is configured',
            check_login=lambda: _Dictable({'logged_in': True}),
            importer_factory=_FakeImporter,
            subscription_factory=_FakeSubscription,
            extractor_factory=_FakeExtractor,
            extractor_site_name='demo',
            playback_handler_factory=_FakePlaybackHandler,
            subtitles_provider_factory=_FakeSubtitlesProvider,
            default_subtitle_lang='en',
            default_subtitle_format='srt',
            mpd_builder_factory=_FakeMpdBuilder,
            proxy_config_builder=lambda domain: {'domain': domain or 'demo.example.com'},
            playlist_rewriter=lambda url, content, referer=None: {
                'content': str(content),
                'media_type': 'application/vnd.apple.mpegurl',
                'headers': {'referer': referer or ''},
                'url': url,
            },
        )

        self.assertEqual(runtime.health().message, 'Demo runtime is configured')
        self.assertEqual(runtime.invoke('check_login_status').data, {'logged_in': True})
        self.assertEqual(runtime.invoke('import_subscriptions').data['total'], 2)
        self.assertEqual(
            runtime.invoke('resolve_subscription', {'url': 'https://example.com/channel/demo'}).data['id'],
            'channel-1',
        )
        self.assertEqual(
            runtime.invoke('sync_subscription', {'url': 'https://example.com/channel/demo'}).data['mode'],
            'incremental',
        )
        self.assertEqual(
            runtime.invoke('extract_video', {'url': 'https://example.com/watch?v=1'}).data['site_name'],
            'demo',
        )
        self.assertEqual(
            runtime.invoke('resolve_playback', {'url': 'https://example.com/watch?v=1', 'video_id': 'video-1'}).data,
            {
                'video_id': 'video-1',
                'url': 'https://example.com/watch?v=1',
                'title': None,
            },
        )
        self.assertEqual(
            runtime.invoke('fetch_subtitles', {'url': 'https://example.com/watch?v=1'}).data['filename'],
            'demo.srt',
        )
        self.assertEqual(
            runtime.invoke('build_mpd', {'url': 'https://example.com/watch?v=1'}).data['content'],
            '<MPD />',
        )
        self.assertEqual(
            runtime.invoke('resolve_proxy_config', {'domain': 'media.example.com'}).data,
            {'domain': 'media.example.com'},
        )
        self.assertEqual(
            runtime.invoke(
                'rewrite_proxy_playlist',
                {'url': 'https://cdn.example.com/master.m3u8', 'content': '#EXTM3U', 'referer': 'https://ref'},
            ).data['headers'],
            {'referer': 'https://ref'},
        )


if __name__ == '__main__':
    unittest.main()
