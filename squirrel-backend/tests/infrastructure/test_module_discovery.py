"""Tests for shared_kernel.infrastructure.module_discovery.

Regression guard: import_classes_from_package(recursive=True) previously used
``pkgutil.walk_packages(package_path)`` WITHOUT a prefix, so the walk could
never recurse into nested subpackages (``__import__('subscription')`` fails
for the relative name) and only the package's direct children were ever
imported. A later attempt added ``prefix=f'{package}.'`` but kept re-prefixing
the yielded names (``f'{package}.{modname}'``), which double-prefixed every
import and discovered nothing at all.
"""

import sys

from infrastructure.database.base import Base
from domains.subscription.domain.models.crawl_job import CrawlJob
from domains.subscription.domain.models.subscription_sync_state import SubscriptionSyncState
from shared_kernel.infrastructure.module_discovery import import_classes_from_package


def test_import_classes_from_package_recursive_discovers_nested_models():
    discovered = import_classes_from_package(
        'domains.subscription',
        base_class=Base,
        recursive=True,
    )

    assert CrawlJob in discovered
    assert SubscriptionSyncState in discovered


def test_import_classes_from_package_recursive_finds_nested_synthetic_package(tmp_path, monkeypatch):
    pkg_dir = tmp_path / 'disc_pkg'
    (pkg_dir / 'nested').mkdir(parents=True)
    (pkg_dir / '__init__.py').write_text('', encoding='utf-8')
    (pkg_dir / 'nested' / '__init__.py').write_text('', encoding='utf-8')
    (pkg_dir / 'nested' / 'mod.py').write_text(
        'class Target:\n    pass\n',
        encoding='utf-8',
    )

    monkeypatch.syspath_prepend(str(tmp_path))
    for name in list(sys.modules):
        if name.startswith('disc_pkg'):
            del sys.modules[name]

    discovered = import_classes_from_package('disc_pkg', recursive=True)

    assert any(cls.__name__ == 'Target' for cls in discovered)
