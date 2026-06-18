import infrastructure.site_catalog.url as url_helper


def test_get_site_from_url_reads_plugin_domains(monkeypatch):
    url_helper.reset_site_lookup_cache()

    class _Registry:
        def build_site_catalog(self):
            return {
                "youtube": {"domains": ["youtube.com", "youtu.be"]},
                "bilibili": {"domains": ["bilibili.com", "b23.tv"]},
            }

    monkeypatch.setattr(url_helper, "get_site_plugin_registry", lambda: _Registry())

    assert url_helper.get_site_from_url("https://www.youtube.com/watch?v=demo") == "youtube"
    assert url_helper.get_site_from_url("https://m.bilibili.com/video/BV1xx411c7mD") == "bilibili"


def test_get_site_from_url_returns_none_when_no_plugin_domain(monkeypatch):
    url_helper.reset_site_lookup_cache()

    class _Registry:
        def build_site_catalog(self):
            return {}

    monkeypatch.setattr(url_helper, "get_site_plugin_registry", lambda: _Registry())

    assert url_helper.get_site_from_url("https://example.com/video/1") is None


def test_get_site_from_url_reuses_cached_registration_index(monkeypatch):
    url_helper.reset_site_lookup_cache()
    registry_calls = {"count": 0}

    class _Registry:
        def build_site_catalog(self):
            registry_calls["count"] += 1
            return {"youtube": {"domains": ["youtube.com", "youtu.be"]}}

    monkeypatch.setattr(url_helper, "get_site_plugin_registry", lambda: _Registry())

    assert url_helper.get_site_from_url("https://www.youtube.com/watch?v=demo") == "youtube"
    assert url_helper.get_site_from_url("https://m.youtube.com/watch?v=demo2") == "youtube"
    assert registry_calls["count"] == 1
