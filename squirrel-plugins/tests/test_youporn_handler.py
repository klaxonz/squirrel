from pathlib import Path
import importlib.util
import sys
from urllib.parse import parse_qs, unquote, urlparse
import unittest
import types
from unittest import mock


ROOT = Path(__file__).resolve().parents[2]
HANDLER_PATH = ROOT / 'squirrel-plugins' / 'youporn' / 'src' / 'squirrel_youporn' / 'handler.py'


def _load_handler_module():
    originals = {name: sys.modules.get(name) for name in ('crawl', 'squirrel_youporn', 'squirrel_youporn.extractor')}

    crawl_module = types.ModuleType('crawl')

    class ParseError(Exception):
        def __init__(self, message, context=None):
            super().__init__(message)
            self.message = message
            self.context = context or {}

    crawl_module.ParseError = ParseError

    package_module = types.ModuleType('squirrel_youporn')
    package_module.__path__ = [str(HANDLER_PATH.parent)]

    extractor_module = types.ModuleType('squirrel_youporn.extractor')
    extractor_module.extract_playback_info = lambda _url: {}

    module_name = 'squirrel_youporn.handler'
    sys.modules.pop(module_name, None)
    module_spec = importlib.util.spec_from_file_location(module_name, HANDLER_PATH)
    module = importlib.util.module_from_spec(module_spec)
    assert module_spec is not None and module_spec.loader is not None

    try:
        sys.modules['crawl'] = crawl_module
        sys.modules['squirrel_youporn'] = package_module
        sys.modules['squirrel_youporn.extractor'] = extractor_module
        sys.modules[module_name] = module
        module_spec.loader.exec_module(module)
        return module
    finally:
        for name, original in originals.items():
            if original is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = original


class YouPornHandlerTests(unittest.TestCase):
    def test_youporn_handler_prefers_hls_manifest_and_wraps_proxy(self):
        youporn_handler = _load_handler_module()

        with mock.patch.object(
            youporn_handler,
            'extract_playback_info',
            lambda _url: {
                'formats': [
                    {
                        'format_id': '720p-http',
                        'url': 'https://cdn.example/video-720.mp4',
                        'protocol': 'https',
                        'height': 720,
                    },
                    {
                        'format_id': 'hls-1080',
                        'url': 'https://cdn.example/video/index.m3u8',
                        'manifest_url': 'https://cdn.example/video/master.m3u8',
                        'protocol': 'm3u8_native',
                        'height': 1080,
                    },
                ],
            },
        ):
            payload = youporn_handler.YouPornHandler().get_video_url(
                type('VideoRef', (), {'url': 'https://www.youporn.com/watch/123456/demo-video/'})()
            )

        self.assertIsNone(payload['audio_url'])
        parsed = urlparse(payload['video_url'])
        params = parse_qs(parsed.query)
        self.assertEqual(params['domain'], ['youporn.com'])
        self.assertEqual(unquote(params['url'][0]), 'https://cdn.example/video/master.m3u8')

    def test_youporn_handler_prefers_progressive_format_for_desktop_clients(self):
        youporn_handler = _load_handler_module()

        with mock.patch.object(
            youporn_handler,
            'extract_playback_info',
            lambda _url: {
                'formats': [
                    {
                        'format_id': '720p-http',
                        'url': 'https://cdn.example/video-720.mp4',
                        'protocol': 'https',
                        'height': 720,
                    },
                    {
                        'format_id': 'hls-1080',
                        'url': 'https://cdn.example/video/index.m3u8',
                        'manifest_url': 'https://cdn.example/video/master.m3u8',
                        'protocol': 'm3u8_native',
                        'height': 1080,
                    },
                ],
            },
        ):
            payload = youporn_handler.YouPornHandler().get_video_url(
                type(
                    'VideoRef',
                    (),
                    {
                        'url': 'https://www.youporn.com/watch/123456/demo-video/',
                        'client_type': 'desktop',
                        'direct_playback': True,
                    },
                )()
            )

        self.assertEqual(
            payload,
            {
                'video_url': 'https://cdn.example/video-720.mp4',
                'audio_url': None,
            },
        )

    def test_youporn_handler_rejects_desktop_hls_fallback_when_no_progressive_stream_exists(self):
        youporn_handler = _load_handler_module()

        with mock.patch.object(
            youporn_handler,
            'extract_playback_info',
            lambda _url: {
                'formats': [
                    {
                        'format_id': 'hls-1080',
                        'url': 'https://cdn.example/video/index.m3u8',
                        'manifest_url': 'https://cdn.example/video/master.m3u8',
                        'protocol': 'm3u8_native',
                        'height': 1080,
                    },
                ],
            },
        ):
            with self.assertRaises(youporn_handler.ParseError) as exc:
                youporn_handler.YouPornHandler().get_video_url(
                    type(
                        'VideoRef',
                        (),
                        {
                            'url': 'https://www.youporn.com/watch/123456/demo-video/',
                            'client_type': 'desktop',
                            'direct_playback': True,
                        },
                    )()
                )

        self.assertIn('Desktop playback requires a direct YouPorn stream', str(exc.exception))

    def test_youporn_handler_falls_back_to_best_progressive_format(self):
        youporn_handler = _load_handler_module()

        with mock.patch.object(
            youporn_handler,
            'extract_playback_info',
            lambda _url: {
                'formats': [
                    {
                        'format_id': '480p-http',
                        'url': 'https://cdn.example/video-480.mp4',
                        'protocol': 'https',
                        'height': 480,
                    },
                    {
                        'format_id': '720p-http',
                        'url': 'https://cdn.example/video-720.mp4',
                        'protocol': 'https',
                        'height': 720,
                    },
                ],
            },
        ):
            payload = youporn_handler.YouPornHandler().get_video_url(
                type('VideoRef', (), {'url': 'https://www.youporn.com/watch/123456/demo-video/'})()
            )

        self.assertEqual(
            payload,
            {
                'video_url': 'https://cdn.example/video-720.mp4',
                'audio_url': None,
            },
        )


if __name__ == '__main__':
    unittest.main()
