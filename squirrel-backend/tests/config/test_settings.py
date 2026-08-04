"""Tests for the config package: lazy proxy, sub-models, env switching, validators.

Note on env isolation: the real ``get_settings`` calls ``load_dotenv(..., override=True)``
on ``.env.<ENV>``, which overwrites process env vars. Tests that need a clean env
stub ``_resolve_env_file`` to point at a non-existent path so dotenv is a no-op,
and then set env vars directly.
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

import pytest


@pytest.fixture
def isolated_settings(monkeypatch):
    """Provide a settings module whose get_settings() does not load any .env file."""
    from infrastructure.config import settings as settings_mod

    monkeypatch.setattr(settings_mod, '_resolve_env_file', lambda: Path('/nonexistent/.env.test-isolation'))
    settings_mod._reset_settings_cache()
    yield settings_mod
    settings_mod._reset_settings_cache()


def test_import_does_not_eagerly_load_settings(monkeypatch):
    """Importing the settings module must not construct the Settings singleton.

    The module exposes ``settings`` as a proxy; the singleton should only be
    built on first attribute access, not at import time.
    """
    monkeypatch.delenv('ENV', raising=False)
    import infrastructure.config.settings as mod

    mod._reset_settings_cache()
    importlib.reload(mod)
    assert mod._settings_instance is None
    assert 'settings' in mod.__dict__
    mod._reset_settings_cache()


def test_from_import_settings_does_not_eagerly_load_settings(monkeypatch):
    monkeypatch.delenv('ENV', raising=False)
    import infrastructure.config.settings as mod

    mod._reset_settings_cache()
    monkeypatch.setattr(mod, '_resolve_env_file', lambda: Path('/nonexistent/.env.test-isolation'))
    from infrastructure.config.settings import settings

    assert mod._settings_instance is None

    monkeypatch.setenv('JWT_SECRET_KEY', 'test-secret-for-ci')
    assert settings.JWT_SECRET_KEY == 'test-secret-for-ci'
    assert mod._settings_instance is not None
    mod._reset_settings_cache()


def test_settings_singleton_is_built_on_first_access(isolated_settings, monkeypatch):
    monkeypatch.setenv('JWT_SECRET_KEY', 'test-secret-for-ci')

    assert isolated_settings._settings_instance is None
    settings_proxy = isolated_settings.settings
    assert isolated_settings._settings_instance is None
    assert settings_proxy.JWT_SECRET_KEY == 'test-secret-for-ci'
    assert isolated_settings._settings_instance is not None


def test_import_main_does_not_eagerly_load_settings(isolated_settings, monkeypatch):
    monkeypatch.delenv('ENV', raising=False)
    monkeypatch.delenv('JWT_SECRET_KEY', raising=False)
    sys.modules.pop('main', None)

    import main  # noqa: F401

    assert isolated_settings._settings_instance is None


def test_nested_redis_settings_read_env_prefix(monkeypatch):
    from infrastructure.config.settings import RedisSettings

    monkeypatch.setenv('REDIS_HOST', '10.0.0.1')
    monkeypatch.setenv('REDIS_PORT', '6390')
    monkeypatch.setenv('REDIS_PASSWORD', 'secret')
    monkeypatch.setenv('REDIS_DB', '0')

    r = RedisSettings()
    assert r.host == '10.0.0.1'
    assert r.port == 6390
    assert r.password == 'secret'
    assert r.db == 0
    assert r.url == 'redis://:secret@10.0.0.1:6390/0'


def test_nested_postgres_settings_read_env_prefix_and_url(monkeypatch):
    from infrastructure.config.settings import PostgresSettings

    monkeypatch.setenv('POSTGRES_HOST', 'db.local')
    monkeypatch.setenv('POSTGRES_PORT', '5433')
    monkeypatch.setenv('POSTGRES_USER', 'app')
    monkeypatch.setenv('POSTGRES_PASSWORD', 'pw')
    monkeypatch.setenv('POSTGRES_DATABASE', 'appdb')

    p = PostgresSettings()
    assert p.host == 'db.local'
    assert p.port == 5433
    assert p.database == 'appdb'
    assert p.url == 'postgresql+psycopg2://app:pw@db.local:5433/appdb'


def test_postgres_password_rejects_default_in_non_dev(monkeypatch):
    from pydantic import ValidationError

    from infrastructure.config.settings import PostgresSettings

    monkeypatch.delenv('ENV', raising=False)
    monkeypatch.setenv('POSTGRES_PASSWORD', 'postgres')

    with pytest.raises(ValidationError):
        PostgresSettings()


def test_postgres_password_allows_default_in_dev(monkeypatch):
    from infrastructure.config.settings import PostgresSettings

    monkeypatch.setenv('ENV', 'dev')
    monkeypatch.setenv('POSTGRES_PASSWORD', 'postgres')

    assert PostgresSettings().password == 'postgres'


def test_crawl_settings_defaults_include_task_type_limits():
    from infrastructure.config.settings import CrawlSettings

    c = CrawlSettings()
    assert c.task_type_limits == {
        'subscription_sync_incremental': 2,
        'subscription_sync_full': 1,
        'video_extract': 8,
    }
    assert c.site_concurrency_overrides == {}
    assert c.default_site_concurrency == 1


def test_crawl_settings_overrides_loaded_from_json_env(monkeypatch):
    from infrastructure.config.settings import CrawlSettings

    monkeypatch.setenv(
        'CRAWL_TASK_TYPE_LIMITS',
        '{"video_extract": 16, "custom_task": 4}',
    )
    monkeypatch.setenv('CRAWL_SITE_CONCURRENCY_OVERRIDES', '{"YouTube": 1}')

    c = CrawlSettings()
    assert c.task_type_limits == {'video_extract': 16, 'custom_task': 4}
    assert c.site_concurrency_overrides == {'youtube': 1}
