from __future__ import annotations

import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]

FILES_WITH_RUNTIME_BOUNDARY = [
    REPO_ROOT / 'squirrel-site-runtimes' / 'javdb' / 'src' / 'squirrel_javdb' / 'html_client.py',
    REPO_ROOT / 'squirrel-site-runtimes' / 'youtube' / 'src' / 'squirrel_youtube' / 'proxy.py',
    REPO_ROOT / 'squirrel-site-runtimes' / 'pornhub' / 'src' / 'squirrel_pornhub' / 'proxy.py',
]


class RuntimeBoundaryTests(unittest.TestCase):
    def test_plugins_do_not_import_backend_cookie_helpers(self):
        for path in FILES_WITH_RUNTIME_BOUNDARY:
            with self.subTest(path=path):
                content = path.read_text(encoding='utf-8')
                self.assertNotIn('utils.cookie', content)


if __name__ == '__main__':
    unittest.main()
