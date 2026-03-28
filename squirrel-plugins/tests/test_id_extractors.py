from __future__ import annotations

import importlib.util
import sys
import types
import unittest
from contextlib import contextmanager
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]

ID_EXTRACTOR_MODULES = {
    'bilibili': {
        'package_root': REPO_ROOT / 'squirrel-plugins' / 'bilibili' / 'src',
        'module': 'squirrel_bilibili.id_extractor',
        'class_name': 'BilibiliIdExtractor',
        'url': 'https://www.bilibili.com/video/BV1xx411c7mD',
        'expected': 'BV1xx411c7mD',
    },
    'javdb': {
        'package_root': REPO_ROOT / 'squirrel-plugins' / 'javdb' / 'src',
        'module': 'squirrel_javdb.id_extractor',
        'class_name': 'JavdbIdExtractor',
        'url': 'https://javdb.com/v/abp-123/',
        'expected': 'abp-123',
    },
    'pornhub': {
        'package_root': REPO_ROOT / 'squirrel-plugins' / 'pornhub' / 'src',
        'module': 'squirrel_pornhub.id_extractor',
        'class_name': 'PornhubIdExtractor',
        'url': 'https://www.pornhub.com/view_video.php?viewkey=ph123456789',
        'expected': 'ph123456789',
    },
    'youtube': {
        'package_root': REPO_ROOT / 'squirrel-plugins' / 'youtube' / 'src',
        'module': 'squirrel_youtube.id_extractor',
        'class_name': 'YoutubeIdExtractor',
        'url': 'https://www.youtube.com/watch?v=dQw4w9WgXcQ',
        'expected': 'dQw4w9WgXcQ',
    },
}


@contextmanager
def _import_paths(*paths: Path):
    original_sys_path = list(sys.path)
    try:
        for path in reversed(paths):
            sys.path.insert(0, str(path))
        yield
    finally:
        sys.path[:] = original_sys_path


@contextmanager
def _stub_crawl_id_extractors():
    original_crawl = sys.modules.get('crawl')

    crawl_module = types.ModuleType('crawl')

    class IdExtractor:
        def __init__(self, url: str):
            self.url = url

    class RegexIdExtractor(IdExtractor):
        pattern = None
        group_index = 1

        def extract_id(self) -> str:
            import re

            if not self.pattern:
                raise NotImplementedError
            match = re.search(self.pattern, self.url)
            if not match:
                raise ValueError(self.url)
            return match.group(self.group_index)

    crawl_module.IdExtractor = IdExtractor
    crawl_module.RegexIdExtractor = RegexIdExtractor

    try:
        sys.modules['crawl'] = crawl_module
        yield
    finally:
        if original_crawl is None:
            sys.modules.pop('crawl', None)
        else:
            sys.modules['crawl'] = original_crawl


def _load_module(name: str):
    spec = ID_EXTRACTOR_MODULES[name]
    with _stub_crawl_id_extractors(), _import_paths(spec['package_root']):
        module_name = f'_id_extractor_test_{name}'
        sys.modules.pop(module_name, None)
        module_path = spec['package_root'] / spec['module'].replace('.', '/')
        file_path = module_path.with_suffix('.py')
        module_spec = importlib.util.spec_from_file_location(module_name, file_path)
        module = importlib.util.module_from_spec(module_spec)
        assert module_spec is not None and module_spec.loader is not None
        sys.modules[module_name] = module
        module_spec.loader.exec_module(module)
        return module


class IdExtractorTests(unittest.TestCase):
    def test_id_extractors_accept_url_constructor_and_extract_expected_id(self):
        for plugin_name, spec in ID_EXTRACTOR_MODULES.items():
            with self.subTest(plugin=plugin_name):
                module = _load_module(plugin_name)
                extractor_cls = getattr(module, spec['class_name'])
                extractor = extractor_cls(spec['url'])
                self.assertEqual(extractor.extract_id(), spec['expected'])


if __name__ == '__main__':
    unittest.main()
