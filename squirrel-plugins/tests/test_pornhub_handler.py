from pathlib import Path
import importlib.util
import sys
from urllib.parse import parse_qs, unquote, urlparse
import unittest
import types


ROOT = Path(__file__).resolve().parents[2]
HANDLER_PATH = ROOT / 'squirrel-plugins' / 'pornhub' / 'src' / 'squirrel_pornhub' / 'handler.py'


def _load_handler_module():
    originals = {
        name: sys.modules.get(name)
        for name in (
            'crawl',
            'phub',
            'base_api',
            'base_api.base',
            'base_api.modules',
            'base_api.modules.config',
        )
    }

    crawl_module = types.ModuleType('crawl')
    crawl_module.VideoUrlHandler = object
    crawl_module.filter_cookies_to_query_string = lambda _url: 'sessid=abc123; platform=pc'
    crawl_module.get_http_headers = lambda _site, headers=None: dict(headers or {})

    base_api_module = types.ModuleType('base_api')
    base_api_base_module = types.ModuleType('base_api.base')
    base_api_modules_module = types.ModuleType('base_api.modules')
    base_api_config_module = types.ModuleType('base_api.modules.config')

    class RuntimeConfig:
        def __init__(self):
            self.timeout = 20
            self.request_delay = 0

    class _FakeSession:
        def __init__(self):
            self.headers = {}
            self.cookies = {}

    class BaseCore:
        def __init__(self, config=None):
            self.config = config
            self.session = _FakeSession()

    base_api_base_module.BaseCore = BaseCore
    base_api_config_module.RuntimeConfig = RuntimeConfig

    phub_module = types.ModuleType('phub')

    class _FakeVideo:
        def __init__(self):
            self.get_m3u8_urls = {
                (1920, 1080): 'https://cdn.example.com/master.m3u8',
            }

    class Client:
        last_instance = None

        def __init__(self, core=None, login=False, language='en'):
            self.core = core
            self.login = login
            self.language = language
            self.got_url = None
            Client.last_instance = self

        def get(self, url):
            self.got_url = url
            return _FakeVideo()

    phub_module.Client = Client

    module_name = 'squirrel_pornhub.handler'
    sys.modules.pop(module_name, None)
    module_spec = importlib.util.spec_from_file_location(module_name, HANDLER_PATH)
    module = importlib.util.module_from_spec(module_spec)
    assert module_spec is not None and module_spec.loader is not None

    try:
        sys.modules['crawl'] = crawl_module
        sys.modules['phub'] = phub_module
        sys.modules['base_api'] = base_api_module
        sys.modules['base_api.base'] = base_api_base_module
        sys.modules['base_api.modules'] = base_api_modules_module
        sys.modules['base_api.modules.config'] = base_api_config_module
        sys.modules[module_name] = module
        module_spec.loader.exec_module(module)
        return module, Client
    finally:
        for name, original in originals.items():
            if original is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = original


class PornhubHandlerTests(unittest.TestCase):
    def test_pornhub_handler_injects_runtime_headers_and_cookies_into_phub_client(self):
        module, client_cls = _load_handler_module()

        payload = module.PornhubHandler().get_video_url(
            type('VideoRef', (), {'url': 'https://www.pornhub.com/view_video.php?viewkey=demo'})()
        )

        client = client_cls.last_instance
        self.assertIsNotNone(client)
        self.assertEqual(client.got_url, 'https://www.pornhub.com/view_video.php?viewkey=demo')
        self.assertEqual(client.core.config.timeout, 30)
        self.assertEqual(client.core.session.headers['Referer'], 'https://www.pornhub.com/')
        self.assertEqual(client.core.session.headers['Origin'], 'https://www.pornhub.com')
        self.assertEqual(client.core.session.cookies['sessid'], 'abc123')
        self.assertEqual(client.core.session.cookies['platform'], 'pc')

        parsed = urlparse(payload['video_url'])
        query = parse_qs(parsed.query)
        self.assertEqual(parsed.path, '/api/video/proxy')
        self.assertEqual(query['domain'], ['pornhub.com'])
        self.assertEqual(unquote(query['url'][0]), 'https://cdn.example.com/master.m3u8')
        self.assertIsNone(payload['audio_url'])


if __name__ == '__main__':
    unittest.main()
