from __future__ import annotations

import importlib
import json
import re
import types
import sys
import tomllib
import unittest
from dataclasses import asdict, dataclass, field
from contextlib import contextmanager
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
PLUGINS_ROOT = REPO_ROOT / 'squirrel-site-runtimes'

PLUGIN_SPECS = {
    'bilibili': {
        'package': 'squirrel_bilibili',
        'expected_dependencies': {'squirrel-sdk', 'yt-dlp'},
    },
    'javdb': {
        'package': 'squirrel_javdb',
        'expected_dependencies': {'squirrel-sdk', 'beautifulsoup4', 'httpx', 'fastapi', 'starlette'},
    },
    'pornhub': {
        'package': 'squirrel_pornhub',
        'expected_dependencies': {'squirrel-sdk', 'beautifulsoup4', 'yt-dlp', 'phub', 'httpx', 'fastapi', 'starlette'},
    },
    'youporn': {
        'package': 'squirrel_youporn',
        'expected_dependencies': {'squirrel-sdk', 'beautifulsoup4', 'yt-dlp', 'httpx', 'fastapi', 'starlette'},
    },
    'youtube': {
        'package': 'squirrel_youtube',
        'expected_dependencies': {'squirrel-sdk', 'beautifulsoup4', 'pytubefix', 'yt-dlp', 'httpx', 'fastapi', 'starlette'},
    },
}

EXPECTED_SITE_LABELS = {
    'bilibili': 'Bilibili',
    'javdb': 'JavDB',
    'pornhub': 'Pornhub',
    'youporn': 'YouPorn',
    'youtube': 'YouTube',
}


def _dependency_names(pyproject_path: Path) -> set[str]:
    data = tomllib.loads(pyproject_path.read_text(encoding='utf-8'))
    dependencies = data.get('project', {}).get('dependencies', [])
    names: set[str] = set()
    for dependency in dependencies:
        match = re.match(r'([A-Za-z0-9_.-]+)', dependency.strip())
        if match:
            names.add(match.group(1).lower())
    return names


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
def _stub_crawl_module():
    original_crawl = sys.modules.get('crawl')

    @dataclass
    class _BaseModel:
        def to_dict(self):
            return asdict(self)

    @dataclass
    class SiteRuntimeCapability(_BaseModel):
        name: str
        description: str = ''
        request_schema: dict = field(default_factory=dict)
        response_schema: dict = field(default_factory=dict)
        timeout_ms: int | None = None
        requires: list[str] = field(default_factory=list)
        metadata: dict = field(default_factory=dict)

    @dataclass
    class SiteRuntimePermission(_BaseModel):
        name: str
        description: str = ''
        required: bool = True
        scope: str | None = None
        metadata: dict = field(default_factory=dict)

    @dataclass
    class SiteRuntimeSite(_BaseModel):
        site_name: str
        domains: list[str] = field(default_factory=list)
        test_url: str | None = None
        features: list[str] = field(default_factory=list)
        metadata: dict = field(default_factory=dict)

    @dataclass
    class SiteRuntimeManifest(_BaseModel):
        runtime_id: str
        version: str
        sdk_api_version: str = '2.0'
        display_name: str = ''
        description: str = ''
        capabilities: list[SiteRuntimeCapability] = field(default_factory=list)
        sites: list[SiteRuntimeSite] = field(default_factory=list)
        permissions: list[SiteRuntimePermission] = field(default_factory=list)
        config_schema: dict = field(default_factory=dict)
        health_policy: dict = field(default_factory=dict)
        metadata: dict = field(default_factory=dict)
        package_name: str | None = None
        entrypoint: str | None = None

    @dataclass
    class SiteRuntimeHealthStatus(_BaseModel):
        healthy: bool
        status: str = 'unknown'
        message: str = ''
        details: dict = field(default_factory=dict)
        checked_at: str | None = None

    @dataclass
    class SubscriptionSyncContext:
        mode: str
        cursor_payload: dict = field(default_factory=dict)
        last_seen_video_url: str | None = None
        limit: int | None = None

    @dataclass
    class VideoMeta(_BaseModel):
        title: str
        url: str
        thumbnail: str | None = None
        duration: int | None = None
        publish_date: str | None = None
        extra_data: dict = field(default_factory=dict)

    @dataclass
    class ExtractionTask:
        url: str
        site_name: str

    class ExtractionResult:
        def __init__(self, payload):
            self._payload = payload

        def to_dict(self):
            return self._payload

        @classmethod
        def success_result(cls, video_meta):
            return cls({'ok': True, 'data': video_meta.to_dict()})

    class _Runtime:
        def __init__(self, manifest):
            self._manifest = manifest

        def manifest(self):
            return self._manifest

    def create_site_runtime(*, manifest, **_kwargs):
        return _Runtime(manifest)

    def create_site_runtime(*, manifest, **_kwargs):
        return _Runtime(manifest)

    crawl_module = types.ModuleType('crawl')
    crawl_module.ExtractionResult = ExtractionResult
    crawl_module.ExtractionTask = ExtractionTask
    crawl_module.SiteRuntimeCapability = SiteRuntimeCapability
    crawl_module.SiteRuntimeHealthStatus = SiteRuntimeHealthStatus
    crawl_module.SiteRuntimeManifest = SiteRuntimeManifest
    crawl_module.SiteRuntimePermission = SiteRuntimePermission
    crawl_module.SiteRuntimeSite = SiteRuntimeSite
    crawl_module.SubscriptionSyncContext = SubscriptionSyncContext
    crawl_module.VideoMeta = VideoMeta
    crawl_module.build_runtime_proxy_config = lambda **_kwargs: {}
    crawl_module.create_site_runtime = create_site_runtime
    crawl_module.create_site_runtime = create_site_runtime
    crawl_module.get_http_headers = lambda _site, headers=None: dict(headers or {})
    crawl_module.get_proxy_config = lambda _site: {}

    try:
        sys.modules['crawl'] = crawl_module
        yield
    finally:
        if original_crawl is None:
            sys.modules.pop('crawl', None)
        else:
            sys.modules['crawl'] = original_crawl


class RuntimeV2PackageTests(unittest.TestCase):
    def test_each_plugin_declares_existing_readme(self):
        for plugin_name in PLUGIN_SPECS:
            with self.subTest(plugin=plugin_name):
                plugin_dir = PLUGINS_ROOT / plugin_name
                pyproject = tomllib.loads((plugin_dir / 'pyproject.toml').read_text(encoding='utf-8'))
                readme_name = pyproject['project']['readme']
                self.assertTrue((plugin_dir / readme_name).exists(), f'{plugin_name} is missing {readme_name}')

    def test_each_plugin_declares_direct_runtime_dependencies(self):
        for plugin_name, spec in PLUGIN_SPECS.items():
            with self.subTest(plugin=plugin_name):
                dependency_names = _dependency_names(PLUGINS_ROOT / plugin_name / 'pyproject.toml')
                self.assertTrue(
                    spec['expected_dependencies'].issubset(dependency_names),
                    f'{plugin_name} dependencies missing: {sorted(spec["expected_dependencies"] - dependency_names)}',
                )

    def test_runtime_manifest_matches_site_runtime_json(self):
        for plugin_name, spec in PLUGIN_SPECS.items():
            with self.subTest(plugin=plugin_name):
                plugin_dir = PLUGINS_ROOT / plugin_name
                runtime_json = json.loads((plugin_dir / 'site-runtime.json').read_text(encoding='utf-8'))
                expected_manifest = runtime_json['manifest']
                with _stub_crawl_module(), _import_paths(plugin_dir / 'src'):
                    module = importlib.import_module(f'{spec["package"]}.runtime')
                    runtime = module.get_site_runtime()
                    actual_manifest = runtime.manifest().to_dict()

                self.assertEqual(actual_manifest['runtime_id'], expected_manifest['runtime_id'])
                self.assertEqual(actual_manifest['version'], expected_manifest['version'])
                self.assertEqual(
                    [item['name'] for item in actual_manifest['capabilities']],
                    [item['name'] for item in expected_manifest['capabilities']],
                )
                self.assertEqual(
                    [item['site_name'] for item in actual_manifest['sites']],
                    [item['site_name'] for item in expected_manifest['sites']],
                )

    def test_runtime_manifest_sites_include_default_site_config_metadata(self):
        for plugin_name, spec in PLUGIN_SPECS.items():
            with self.subTest(plugin=plugin_name):
                plugin_dir = PLUGINS_ROOT / plugin_name
                runtime_json = json.loads((plugin_dir / 'site-runtime.json').read_text(encoding='utf-8'))

                with _stub_crawl_module(), _import_paths(plugin_dir / 'src'):
                    module = importlib.import_module(f'{spec["package"]}.runtime')
                    runtime = module.get_site_runtime()
                    manifest = runtime.manifest().to_dict()

                expected_site = runtime_json['manifest']['sites'][0]
                actual_site = manifest['sites'][0]
                actual_metadata = actual_site.get('metadata') or {}
                expected_metadata = expected_site.get('metadata') or {}

                self.assertEqual(actual_metadata, expected_metadata)
                self.assertEqual(actual_metadata.get('label'), EXPECTED_SITE_LABELS[plugin_name])
                for key in ('http', 'proxy', 'login', 'rate_limit', 'metadata'):
                    self.assertIn(key, actual_metadata, f'{plugin_name} site metadata missing {key}')

    def test_javdb_login_status_timeout_budget_is_large_enough_for_cloudflare_bypass(self):
        plugin_dir = PLUGINS_ROOT / 'javdb'
        runtime_json = json.loads((plugin_dir / 'site-runtime.json').read_text(encoding='utf-8'))
        metadata_capability = next(
            item for item in runtime_json['manifest']['capabilities'] if item['name'] == 'check_login_status'
        )

        with _stub_crawl_module(), _import_paths(plugin_dir / 'src'):
            module = importlib.import_module('squirrel_javdb.runtime')
            runtime = module.get_site_runtime()
            runtime_capability = next(
                item.to_dict() for item in runtime.manifest().capabilities if item.name == 'check_login_status'
            )

        self.assertGreaterEqual(runtime_capability['timeout_ms'], 30000)
        self.assertGreaterEqual(metadata_capability['timeout_ms'], 30000)

    def test_javdb_import_subscriptions_timeout_budget_is_large_enough_for_multi_page_fetches(self):
        plugin_dir = PLUGINS_ROOT / 'javdb'
        runtime_json = json.loads((plugin_dir / 'site-runtime.json').read_text(encoding='utf-8'))
        metadata_capability = next(
            item for item in runtime_json['manifest']['capabilities'] if item['name'] == 'import_subscriptions'
        )

        with _stub_crawl_module(), _import_paths(plugin_dir / 'src'):
            module = importlib.import_module('squirrel_javdb.runtime')
            runtime = module.get_site_runtime()
            runtime_capability = next(
                item.to_dict() for item in runtime.manifest().capabilities if item.name == 'import_subscriptions'
            )

        self.assertGreaterEqual(runtime_capability['timeout_ms'], 120000)
        self.assertGreaterEqual(metadata_capability['timeout_ms'], 120000)

    def test_bilibili_sync_subscription_timeout_budget_is_large_enough_for_slow_feed_fetches(self):
        plugin_dir = PLUGINS_ROOT / 'bilibili'
        runtime_json = json.loads((plugin_dir / 'site-runtime.json').read_text(encoding='utf-8'))
        metadata_capability = next(
            item for item in runtime_json['manifest']['capabilities'] if item['name'] == 'sync_subscription'
        )

        with _stub_crawl_module(), _import_paths(plugin_dir / 'src'):
            module = importlib.import_module('squirrel_bilibili.runtime')
            runtime = module.get_site_runtime()
            runtime_capability = next(
                item.to_dict() for item in runtime.manifest().capabilities if item.name == 'sync_subscription'
            )

        self.assertGreaterEqual(runtime_capability['timeout_ms'], 120000)
        self.assertGreaterEqual(metadata_capability['timeout_ms'], 120000)

    def test_javdb_sync_subscription_timeout_budget_is_large_enough_for_slow_feed_fetches(self):
        plugin_dir = PLUGINS_ROOT / 'javdb'
        runtime_json = json.loads((plugin_dir / 'site-runtime.json').read_text(encoding='utf-8'))
        metadata_capability = next(
            item for item in runtime_json['manifest']['capabilities'] if item['name'] == 'sync_subscription'
        )

        with _stub_crawl_module(), _import_paths(plugin_dir / 'src'):
            module = importlib.import_module('squirrel_javdb.runtime')
            runtime = module.get_site_runtime()
            runtime_capability = next(
                item.to_dict() for item in runtime.manifest().capabilities if item.name == 'sync_subscription'
            )

        self.assertGreaterEqual(runtime_capability['timeout_ms'], 120000)
        self.assertGreaterEqual(metadata_capability['timeout_ms'], 120000)

    def test_youporn_import_subscriptions_timeout_budget_is_large_enough_for_multi_page_fetches(self):
        plugin_dir = PLUGINS_ROOT / 'youporn'
        runtime_json = json.loads((plugin_dir / 'site-runtime.json').read_text(encoding='utf-8'))
        metadata_capability = next(
            item for item in runtime_json['manifest']['capabilities'] if item['name'] == 'import_subscriptions'
        )

        with _stub_crawl_module(), _import_paths(plugin_dir / 'src'):
            module = importlib.import_module('squirrel_youporn.runtime')
            runtime = module.get_site_runtime()
            runtime_capability = next(
                item.to_dict() for item in runtime.manifest().capabilities if item.name == 'import_subscriptions'
            )

        self.assertGreaterEqual(runtime_capability['timeout_ms'], 30000)
        self.assertGreaterEqual(metadata_capability['timeout_ms'], 30000)


if __name__ == '__main__':
    unittest.main()
