"""Tests for the config package: lazy proxy, sub-models, env switching, validators.

Note on env isolation: the real ``get_settings`` calls ``load_dotenv(..., override=True)``
on ``.env.<ENV>``, which overwrites process env vars. Tests that need a clean env
stub ``_resolve_env_file`` to point at a non-existent path so dotenv is a no-op,
and then set env vars directly.
"""
from __future__ import annotations

import importlib
from pathlib import Path

import pytest


@pytest.fixture
def isolated_settings(monkeypatch):
    """Provide a settings module whose get_settings() does not load any .env file."""
    from infrastructure.config import settings as settings_mod

    monkeypatch.setattr(settings_mod, "_resolve_env_file", lambda: Path("/nonexistent/.env.test-isolation"))
    settings_mod._reset_settings_cache()
    yield settings_mod
    settings_mod._reset_settings_cache()


def test_import_does_not_eagerly_load_settings(monkeypatch):
    """Importing the settings module must not construct the Settings singleton.

    The module exposes ``settings`` via PEP 562 ``__getattr__``; the singleton
    should only be built on first attribute access, not at import time.
    Reloading the module re-executes module-level code — if it eagerly assigned
    ``settings = get_settings()``, _settings_instance would be populated right
    after reload. It stays None, proving lazy resolution.
    """
    monkeypatch.delenv("ENV", raising=False)
    import infrastructure.config.settings as mod

    mod._reset_settings_cache()
    importlib.reload(mod)
    # No singleton built by import alone.
    assert mod._settings_instance is None
    # `settings` is not a real module attribute; it must go through __getattr__.
    assert "settings" not in mod.__dict__
    mod._reset_settings_cache()


def test_settings_singleton_is_built_on_first_access(isolated_settings, monkeypatch):
    monkeypatch.setenv("JWT_SECRET_KEY", "test-secret-for-ci")

    assert isolated_settings._settings_instance is None
    s = isolated_settings.settings  # triggers lazy load
    assert isolated_settings._settings_instance is s
    assert s.JWT_SECRET_KEY == "test-secret-for-ci"


def test_nested_redis_settings_read_env_prefix(monkeypatch):
    from infrastructure.config.settings import RedisSettings

    monkeypatch.setenv("REDIS_HOST", "10.0.0.1")
    monkeypatch.setenv("REDIS_PORT", "6390")
    monkeypatch.setenv("REDIS_PASSWORD", "secret")
    monkeypatch.setenv("REDIS_DB", "0")

    r = RedisSettings()
    assert r.host == "10.0.0.1"
    assert r.port == 6390
    assert r.password == "secret"
    assert r.db == 0
    assert r.url == "redis://:secret@10.0.0.1:6390/0"


def test_nested_postgres_settings_read_env_prefix_and_url(monkeypatch):
    from infrastructure.config.settings import PostgresSettings

    monkeypatch.setenv("POSTGRES_HOST", "db.local")
    monkeypatch.setenv("POSTGRES_PORT", "5433")
    monkeypatch.setenv("POSTGRES_USER", "app")
    monkeypatch.setenv("POSTGRES_PASSWORD", "pw")
    monkeypatch.setenv("POSTGRES_DATABASE", "appdb")

    p = PostgresSettings()
    assert p.host == "db.local"
    assert p.port == 5433
    assert p.database == "appdb"
    assert p.url == "postgresql+psycopg2://app:pw@db.local:5433/appdb"


def test_postgres_password_rejects_default_in_non_dev(monkeypatch):
    from pydantic import ValidationError

    from infrastructure.config.settings import PostgresSettings

    monkeypatch.delenv("ENV", raising=False)
    monkeypatch.setenv("POSTGRES_PASSWORD", "postgres")

    with pytest.raises(ValidationError):
        PostgresSettings()


def test_postgres_password_allows_default_in_dev(monkeypatch):
    from infrastructure.config.settings import PostgresSettings

    monkeypatch.setenv("ENV", "dev")
    monkeypatch.setenv("POSTGRES_PASSWORD", "postgres")

    assert PostgresSettings().password == "postgres"


def test_crawl_settings_defaults_include_task_type_limits():
    from infrastructure.config.settings import CrawlSettings

    c = CrawlSettings()
    assert c.task_type_limits == {
        "subscription_sync_incremental": 2,
        "subscription_sync_full": 1,
        "video_extract": 8,
    }
    assert c.site_concurrency_overrides == {}
    assert c.default_site_concurrency == 2


def test_crawl_settings_overrides_loaded_from_json_env(monkeypatch):
    from infrastructure.config.settings import CrawlSettings

    monkeypatch.setenv(
        "CRAWL_TASK_TYPE_LIMITS",
        '{"video_extract": 16, "custom_task": 4}',
    )
    monkeypatch.setenv("CRAWL_SITE_CONCURRENCY_OVERRIDES", '{"javdb": 6}')

    c = CrawlSettings()
    assert c.task_type_limits == {"video_extract": 16, "custom_task": 4}
    assert c.site_concurrency_overrides == {"javdb": 6}


def test_mq_settings_keeps_overrides_as_string():
    """MQ_CONSUMER_COUNT_OVERRIDES stays a raw string to preserve wildcard syntax."""
    from infrastructure.config.settings import MqSettings

    m = MqSettings()
    assert m.consumer_count_overrides == ""
    assert m.consumer_default_count == 1


def test_cookiecloud_settings_read_env_prefix(monkeypatch):
    from infrastructure.config.settings import CookieCloudSettings

    monkeypatch.setenv("COOKIECLOUD_URL", "https://cc.example.com")
    monkeypatch.setenv("COOKIECLOUD_UUID", "abc-123")
    monkeypatch.setenv("COOKIECLOUD_PASSWORD", "secret")

    cc = CookieCloudSettings()
    assert cc.url == "https://cc.example.com"
    assert cc.uuid == "abc-123"
    assert cc.password == "secret"
    assert cc.is_configured is True


def test_cookiecloud_settings_unconfigured_when_any_field_missing(monkeypatch):
    from infrastructure.config.settings import CookieCloudSettings

    monkeypatch.delenv("COOKIECLOUD_URL", raising=False)
    monkeypatch.delenv("COOKIECLOUD_UUID", raising=False)
    monkeypatch.delenv("COOKIECLOUD_PASSWORD", raising=False)

    cc = CookieCloudSettings()
    assert cc.is_configured is False

    monkeypatch.setenv("COOKIECLOUD_URL", "https://cc.example.com")
    monkeypatch.setenv("COOKIECLOUD_UUID", "abc-123")
    # password still unset
    assert CookieCloudSettings().is_configured is False


def test_kugou_music_settings_read_env_prefix(monkeypatch):
    from infrastructure.config.settings import KugouMusicSettings

    monkeypatch.setenv("KUGOU_MUSIC_API_BASE_URL", "http://localhost:3000")
    monkeypatch.setenv("KUGOU_MUSIC_COOKIE", "token=abc;userid=1")

    k = KugouMusicSettings()
    assert k.api_base_url == "http://localhost:3000"
    assert k.cookie == "token=abc;userid=1"


def test_config_package_reexports_classes():
    """The package re-exports the public settings classes/helpers (not the singleton).

    ``settings`` itself is intentionally not re-exported because the
    ``infrastructure.config.settings`` submodule shadows a package-level binding;
    callers use ``from infrastructure.config.settings import settings``.
    """
    import infrastructure.config as pkg

    for name in ("Settings", "RedisSettings", "PostgresSettings", "MeiliSettings", "CrawlSettings", "MqSettings", "CookieCloudSettings", "KugouMusicSettings", "get_settings", "StartupIssues"):
        assert hasattr(pkg, name), f"missing re-export: {name}"


def test_settings_database_url_forwards_to_postgres_submodel(isolated_settings, monkeypatch):
    monkeypatch.setenv("JWT_SECRET_KEY", "k")
    monkeypatch.setenv("POSTGRES_HOST", "h")
    monkeypatch.setenv("POSTGRES_PORT", "1")
    monkeypatch.setenv("POSTGRES_USER", "u")
    monkeypatch.setenv("POSTGRES_PASSWORD", "p")
    monkeypatch.setenv("POSTGRES_DATABASE", "d")

    s = isolated_settings.settings
    assert s.database_url == "postgresql+psycopg2://u:p@h:1/d"
    assert s.database_url == s.postgres.url


def test_reset_sub_settings_cache_rebuilds_from_env(monkeypatch):
    from infrastructure.config.settings import _get_redis_settings, reset_sub_settings_cache

    reset_sub_settings_cache()
    monkeypatch.setenv("REDIS_HOST", "first.example.com")
    first = _get_redis_settings()
    assert first.host == "first.example.com"

    # Env changed but cache holds the old singleton until cleared.
    monkeypatch.setenv("REDIS_HOST", "second.example.com")
    assert _get_redis_settings().host == "first.example.com"

    reset_sub_settings_cache()
    assert _get_redis_settings().host == "second.example.com"
    reset_sub_settings_cache()


def test_optional_feature_warnings_empty_when_all_configured(isolated_settings, monkeypatch):
    monkeypatch.setenv("JWT_SECRET_KEY", "k")
    monkeypatch.setenv("COOKIECLOUD_URL", "https://cc.example.com")
    monkeypatch.setenv("COOKIECLOUD_UUID", "u")
    monkeypatch.setenv("COOKIECLOUD_PASSWORD", "p")
    monkeypatch.setenv("KUGOU_MUSIC_API_BASE_URL", "http://localhost:3000")

    s = isolated_settings.settings
    assert s.optional_feature_warnings() == []


def test_optional_feature_warnings_reports_missing_cookiecloud_and_kugou(isolated_settings, monkeypatch):
    monkeypatch.setenv("JWT_SECRET_KEY", "k")
    monkeypatch.delenv("COOKIECLOUD_URL", raising=False)
    monkeypatch.delenv("COOKIECLOUD_UUID", raising=False)
    monkeypatch.delenv("COOKIECLOUD_PASSWORD", raising=False)
    monkeypatch.delenv("KUGOU_MUSIC_API_BASE_URL", raising=False)

    warnings = isolated_settings.settings.optional_feature_warnings()
    assert any("CookieCloud" in w for w in warnings)
    assert any("KUGOU_MUSIC" in w for w in warnings)


def test_settings_construction_does_not_log(isolated_settings, monkeypatch, caplog):
    """Constructing Settings must NOT emit warnings — optional-feature notices
    are a pure query (optional_feature_warnings), surfaced only by startup
    entrypoints. This keeps tests/alembic/scripts spam-free.
    """
    import logging

    monkeypatch.setenv("JWT_SECRET_KEY", "k")
    # Leave CookieCloud / Kugou unset so the old model_post_init WOULD have warned.
    monkeypatch.delenv("COOKIECLOUD_PASSWORD", raising=False)
    monkeypatch.delenv("KUGOU_MUSIC_API_BASE_URL", raising=False)

    with caplog.at_level(logging.WARNING, logger="infrastructure.config.settings"):
        _ = isolated_settings.settings

    assert not any("not configured" in r.message for r in caplog.records)
    assert not any("unavailable" in r.message for r in caplog.records)
