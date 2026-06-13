import asyncio
import sys
from pathlib import Path
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from routes import sites as site_routes
from routes.site_cookies import bulk_import as site_cookie_bulk_import
from routes.site_cookies import single_upload as site_cookie_single_upload


class FakeCatalogService:
    def __init__(self, catalog, saved_catalog=None):
        self._catalog = catalog
        self._saved_catalog = saved_catalog or catalog

    @staticmethod
    def build_site_info(site_name, catalog):
        entry = catalog.get(site_name.lower())
        if not entry:
            return None
        return {"name": site_name.lower(), "site_name": site_name.lower(), **entry}

    @staticmethod
    def merge_site_names(catalog):
        return sorted(catalog)

    @staticmethod
    def normalize_cookie_domain(domain):
        return domain.strip().lstrip(".").lower()

    def get_merged_site_catalog(self):
        return self._catalog

    def save_site_overrides(self, payload):
        return self._saved_catalog


class FakeLoginService:
    def __init__(self, supported_sites=None, status=None):
        self._supported_sites = supported_sites or set()
        self._status = status or {}

    def get_supported_sites(self):
        return self._supported_sites

    def test_site_login_status(self, site_name):
        return self._status or {"supported": True, "logged_in": True, "site_name": site_name}


def test_get_supported_sites_merges_runtime_sites_when_catalog_is_partial(monkeypatch):
    effective_catalog = {
        "youtube": {
            "label": "YouTube",
            "domains": ["youtube.com", "youtu.be"],
            "enabled": True,
            "test_url": "https://www.youtube.com",
            "icon_url": "/api/sites/youtube/icon",
        },
        "bilibili": {
            "label": "Bilibili",
            "domains": ["bilibili.com"],
            "enabled": True,
            "test_url": "https://www.bilibili.com",
        },
    }

    response = site_routes.catalog.get_supported_sites(
        catalog_svc=FakeCatalogService(effective_catalog),
        login_svc=FakeLoginService({"bilibili"}),
    )

    assert response["code"] == 0

    sites = response["data"]["sites"]
    site_names = {site["site_name"] for site in sites}
    assert site_names == {"youtube", "bilibili"}

    youtube = next(site for site in sites if site["site_name"] == "youtube")
    bilibili = next(site for site in sites if site["site_name"] == "bilibili")

    assert youtube["icon_url"] == "/api/sites/youtube/icon"
    assert bilibili["domains"] == ["bilibili.com"]
    assert bilibili["supports_login_status"] is True


def test_sites_api_returns_list_and_catalog_on_explicit_paths(monkeypatch):
    effective_catalog = {
        "youtube": {
            "label": "YouTube",
            "domains": ["youtube.com"],
            "enabled": True,
            "test_url": "https://www.youtube.com",
        },
    }

    app = FastAPI()
    app.include_router(site_routes.router)
    app.dependency_overrides[site_routes.dependencies.get_catalog_service] = lambda: FakeCatalogService(effective_catalog)
    app.dependency_overrides[site_routes.dependencies.get_login_service] = lambda: FakeLoginService()
    client = TestClient(app)

    sites_response = client.get("/api/sites")
    catalog_response = client.get("/api/sites/catalog")

    assert sites_response.status_code == 200
    assert sites_response.json()["data"]["sites"][0]["site_name"] == "youtube"
    assert catalog_response.status_code == 200
    assert catalog_response.json()["data"] == effective_catalog


def test_update_sites_catalog_accepts_override_payload(monkeypatch):
    saved_catalog = {"youtube": {"enabled": False, "domains": ["youtube.com"]}}

    app = FastAPI()
    app.include_router(site_routes.router)
    app.dependency_overrides[site_routes.dependencies.get_catalog_service] = lambda: FakeCatalogService({}, saved_catalog)
    client = TestClient(app)

    response = client.put("/api/sites/catalog", json={"sites": {"youtube": {"enabled": False}}})

    assert response.status_code == 200
    assert response.json()["code"] == 0
    assert response.json()["data"]["youtube"]["enabled"] is False


def test_upload_site_cookies_accepts_runtime_only_site(monkeypatch, tmp_path):
    effective_catalog = {
        "youporn": {
            "label": "YouPorn",
            "domains": ["youporn.com"],
            "enabled": True,
            "test_url": "https://www.youporn.com",
        },
    }
    cookies_path = tmp_path / "youporn.txt"

    monkeypatch.setattr(site_cookie_single_upload, "get_site_cookies_file_path", lambda site_name: cookies_path)

    class DummyUploadFile:
        filename = "cookies.txt"

        async def read(self):
            return (
                b"# Netscape HTTP Cookie File\n"
                b".youporn.com\tTRUE\t/\tFALSE\t0\tsession\tabc123\n"
            )

    response = asyncio.run(site_cookie_single_upload.upload_site_cookies(
        "youporn",
        DummyUploadFile(),
        catalog_svc=FakeCatalogService(effective_catalog),
        login_svc=FakeLoginService(),
    ))

    assert response["code"] == 0
    assert response["data"]["site_name"] == "youporn"
    assert ".youporn.com" in cookies_path.read_text(encoding="utf-8")


def test_upload_site_cookies_uses_safe_cookie_file_writer(monkeypatch, tmp_path):
    effective_catalog = {
        "youporn": {
            "label": "YouPorn",
            "domains": ["youporn.com"],
            "enabled": True,
            "test_url": "https://www.youporn.com",
        },
    }
    cookies_path = tmp_path / "youporn.txt"
    writes = []

    monkeypatch.setattr(site_cookie_single_upload, "get_site_cookies_file_path", lambda site_name: cookies_path)

    def _record_write(path, content):
        writes.append((path, content))
        path.write_text(content, encoding="utf-8")

    monkeypatch.setattr(
        site_cookie_single_upload,
        "write_cookie_text_file",
        _record_write,
        raising=False,
    )

    class DummyUploadFile:
        filename = "cookies.txt"

        async def read(self):
            return (
                b"# Netscape HTTP Cookie File\n"
                b".youporn.com\tTRUE\t/\tFALSE\t0\tsession\tabc123\n"
            )

    response = asyncio.run(site_cookie_single_upload.upload_site_cookies(
        "youporn",
        DummyUploadFile(),
        catalog_svc=FakeCatalogService(effective_catalog),
        login_svc=FakeLoginService(),
    ))

    assert response["code"] == 0
    assert writes == [
        (
            cookies_path,
            "# Netscape HTTP Cookie File\n"
            ".youporn.com\tTRUE\t/\tFALSE\t0\tsession\tabc123\n",
        ),
    ]


def test_import_all_site_cookies_uses_safe_cookie_file_writer(monkeypatch, tmp_path):
    effective_catalog = {
        "youporn": {
            "label": "YouPorn",
            "domains": ["youporn.com"],
            "enabled": True,
            "test_url": "https://www.youporn.com",
        },
    }
    cookies_path = tmp_path / "youporn.txt"
    writes = []

    monkeypatch.setattr(site_cookie_bulk_import, "get_site_cookies_file_path", lambda site_name: cookies_path)
    monkeypatch.setattr(
        site_cookie_bulk_import,
        "write_cookie_text_file",
        lambda path, content: writes.append((path, content)),
        raising=False,
    )

    class DummyUploadFile:
        filename = "cookies.txt"

        async def read(self):
            return (
                b"# Netscape HTTP Cookie File\n"
                b".youporn.com\tTRUE\t/\tFALSE\t0\tsession\tabc123\n"
            )

    response = asyncio.run(site_cookie_bulk_import.import_cookies_for_all_sites(
        DummyUploadFile(),
        catalog_svc=FakeCatalogService(effective_catalog),
    ))

    assert response["code"] == 0
    assert writes == [
        (
            cookies_path,
            "# Netscape HTTP Cookie File\n"
            ".youporn.com\tTRUE\t/\tFALSE\t0\tsession\tabc123\n",
        ),
    ]


def test_get_site_login_status_includes_youtube_oauth_state(monkeypatch):
    catalog = {"youtube": {"label": "YouTube", "domains": ["youtube.com"], "enabled": True}}
    monkeypatch.setitem(
        sys.modules,
        "services.site_catalog.youtube_oauth",
        SimpleNamespace(
            get_oauth_state=lambda timeout_seconds=5.0: SimpleNamespace(
                status="authenticated",
                account=SimpleNamespace(name="YT User", email="yt@example.com", avatar="https://img.example.com/a.png"),
            ),
        ),
    )

    response = site_routes.login.get_site_login_status(
        "youtube",
        catalog_svc=FakeCatalogService(catalog),
        login_svc=FakeLoginService(status={"supported": True, "logged_in": False, "site_name": "youtube"}),
    )

    assert response["code"] == 0
    assert response["data"]["oauth_status"] == "authenticated"
    assert response["data"]["oauth_account"]["email"] == "yt@example.com"

