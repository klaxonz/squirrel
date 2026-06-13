import sys
from pathlib import Path
from types import SimpleNamespace

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import services.video.extraction.thumbnail_downloader as thumbnail_downloader
from services.video.extraction.thumbnail import headers as thumbnail_headers
from services.video.extraction.thumbnail import html as thumbnail_html
from services.video.extraction.thumbnail import local_index as thumbnail_local_index
from services.video.extraction.thumbnail.client import ThumbnailHttpClient
from services.video.extraction.thumbnail.headers import ThumbnailSiteConfig
from services.video.extraction.thumbnail.local_index import ThumbnailLocalIndexRepository
from services.video.extraction.thumbnail.storage import ThumbnailStorage
from services.video.extraction.thumbnail_downloader import ThumbnailDownloaderService


def _thumbnail_service_with_fake_http(monkeypatch, tmp_path, fake_get):
    storage = ThumbnailStorage()
    http_client = ThumbnailHttpClient()
    site_config = ThumbnailSiteConfig()

    monkeypatch.setattr(storage, 'get_batch_dir', lambda video_id: str(tmp_path / 'batch_001'))
    monkeypatch.setattr(storage, 'get_extension', lambda remote_url: '.jpg')
    monkeypatch.setattr(http_client, '_get_http_client', lambda: SimpleNamespace(get=fake_get))
    monkeypatch.setattr(site_config, 'should_download', lambda site_name: True)
    monkeypatch.setattr(site_config, 'site_info', lambda site_name: {})
    monkeypatch.setattr(site_config, 'site_requires_cookies', lambda site_name: False)

    return ThumbnailDownloaderService(
        site_config=site_config,
        storage=storage,
        local_index=SimpleNamespace(upsert=lambda *args, **kwargs: None),
        http_client=http_client,
    )


def _site_config_with_download_enabled(monkeypatch):
    site_config = ThumbnailSiteConfig()
    monkeypatch.setattr(site_config, 'should_download', lambda site_name: True)
    monkeypatch.setattr(site_config, 'site_info', lambda site_name: {})
    monkeypatch.setattr(site_config, 'site_requires_cookies', lambda site_name: False)
    return site_config


def test_bulk_thumbnail_lookup_uses_direct_local_file_check(monkeypatch):
    storage = SimpleNamespace(
        get_local_thumbnail_path=lambda video_id, remote_url=None: (
            '/static/thumbnails/batch-1/11.jpg' if video_id == 11 else None
        ),
    )
    service = ThumbnailDownloaderService(
        site_config=SimpleNamespace(should_use_offline=lambda site_name: True),
        storage=storage,
        local_index=SimpleNamespace(get_local_thumbnail_path_map=lambda indexed_items: {}),
    )
    monkeypatch.setattr(thumbnail_downloader, 'get_site_from_url', lambda video_url: 'pornhub')

    results = service.get_thumbnail_url_map([
        (11, 'https://img.example.com/11.jpg', 'https://www.pornhub.com/view_video.php?viewkey=11'),
        (12, 'https://img.example.com/12.jpg', 'https://www.pornhub.com/view_video.php?viewkey=12'),
    ])

    assert results == {
        11: '/static/thumbnails/batch-1/11.jpg',
        12: 'https://img.example.com/12.jpg',
    }


def test_bulk_thumbnail_lookup_prefers_local_index(monkeypatch):
    fallback_calls = []
    service = ThumbnailDownloaderService(
        site_config=SimpleNamespace(should_use_offline=lambda site_name: True),
        storage=SimpleNamespace(
            get_local_thumbnail_path=lambda video_id, remote_url=None: fallback_calls.append(
                (video_id, remote_url),
            ) or None,
        ),
        local_index=SimpleNamespace(
            get_local_thumbnail_path_map=lambda indexed_items: {
                21: '/static/thumbnails/batch_001/21.webp',
            },
        ),
    )
    monkeypatch.setattr(thumbnail_downloader, 'get_site_from_url', lambda video_url: 'pornhub')

    results = service.get_thumbnail_url_map([
        (21, 'https://img.example.com/21.webp', 'https://www.pornhub.com/view_video.php?viewkey=21'),
        (22, 'https://img.example.com/22.webp', 'https://www.pornhub.com/view_video.php?viewkey=22'),
    ])

    assert results == {
        21: '/static/thumbnails/batch_001/21.webp',
        22: 'https://img.example.com/22.webp',
    }
    assert fallback_calls == [
        (22, 'https://img.example.com/22.webp'),
    ]


def test_local_thumbnail_path_map_skips_stale_index_entries(monkeypatch):
    storage = ThumbnailStorage()
    repository = ThumbnailLocalIndexRepository(storage)
    index_updates = []

    rows = [
        SimpleNamespace(video_id=31, batch_name='batch_001', filename='31.jpg'),
        SimpleNamespace(video_id=32, batch_name='batch_001', filename='32.jpg'),
    ]

    class _FakeSession:
        def execute(self, _statement):
            return SimpleNamespace(all=lambda: rows)

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(thumbnail_local_index, 'get_session', lambda: _FakeSession())
    monkeypatch.setattr(
        thumbnail_local_index.os.path,
        'exists',
        lambda path: path.replace('\\', '/').endswith('/32.jpg'),
    )
    monkeypatch.setattr(
        repository,
        'upsert',
        lambda video_id, batch_name, filename, exists=True: index_updates.append(
            (video_id, batch_name, filename, exists),
        ),
        raising=False,
    )

    results = repository.get_local_thumbnail_path_map([
        (31, 'https://img.example.com/31.jpg', 'https://www.youtube.com/watch?v=31'),
        (32, 'https://img.example.com/32.jpg', 'https://www.youtube.com/watch?v=32'),
    ])

    assert results == {
        32: '/static/thumbnails/batch_001/32.jpg',
    }
    assert index_updates == [
        (31, 'batch_001', '31.jpg', False),
    ]


def test_download_thumbnail_updates_local_index(monkeypatch, tmp_path):
    index_updates = []
    storage = ThumbnailStorage()
    monkeypatch.setattr(storage, 'get_batch_dir', lambda video_id: str(tmp_path / 'batch_001'))
    monkeypatch.setattr(storage, 'get_extension', lambda remote_url: '.jpg')
    service = ThumbnailDownloaderService(
        site_config=_site_config_with_download_enabled(monkeypatch),
        storage=storage,
        local_index=SimpleNamespace(
            upsert=lambda video_id, batch_name, filename, exists=True: index_updates.append(
                (video_id, batch_name, filename, exists),
            ),
        ),
        http_client=SimpleNamespace(
            request_thumbnail=lambda url, headers, video_id: SimpleNamespace(
                status_code=200,
                headers={'content-type': 'image/jpeg'},
                content=b'image-bytes',
            ),
        ),
    )

    file_path = service.download_thumbnail(
        video_id=42,
        thumbnail_url='https://img.example.com/42.jpg',
        site_name='youtube',
    )

    assert file_path == str(tmp_path / 'batch_001' / '42.jpg')
    assert index_updates == [
        (42, 'batch_001', '42.jpg', True),
    ]


def test_download_thumbnail_retries_transport_error(monkeypatch, tmp_path):
    http_client = ThumbnailHttpClient()
    clients = [
        SimpleNamespace(
            get=lambda url, headers=None: (_ for _ in ()).throw(httpx.ConnectError('boom')),
        ),
        SimpleNamespace(
            get=lambda url, headers=None: SimpleNamespace(
                status_code=200,
                headers={'content-type': 'image/png'},
                content=b'image-bytes',
            ),
        ),
    ]
    storage = ThumbnailStorage()

    monkeypatch.setattr(storage, 'get_batch_dir', lambda video_id: str(tmp_path / 'batch_001'))
    monkeypatch.setattr(storage, 'get_extension', lambda remote_url: '.png')
    monkeypatch.setattr(http_client, '_get_http_client', lambda: clients.pop(0))
    monkeypatch.setattr(http_client, 'close', lambda: None)
    monkeypatch.setattr(http_client, '_download_retry_delay', lambda attempt: 0)

    service = ThumbnailDownloaderService(
        site_config=_site_config_with_download_enabled(monkeypatch),
        storage=storage,
        local_index=SimpleNamespace(upsert=lambda *args, **kwargs: None),
        http_client=http_client,
    )

    file_path = service.download_thumbnail(
        video_id=77,
        thumbnail_url='https://img.example.com/77.png',
        site_name='pornhub',
        source_url='https://www.pornhub.com/view_video.php?viewkey=demo',
    )

    assert file_path == str(tmp_path / 'batch_001' / '77.png')
    assert clients == []


def test_extract_thumbnail_url_prefers_long_lived_preview():
    short_url = (
        "https://pix-fl.phncdn.com/c6251/videos/demo/original.jpg/plain/"
        "rs:fit:640:360?hdnea=st=1777096861~exp=1777183261~hdl=-1~hmac=short"
    )
    long_url = (
        "https://pix-egi.phncdn.com/c6251/videos/demo/original.jpg/plain/"
        "rs:fit:350:196?validfrom=1751342400&validto=4891363200&hash=long"
    )
    html = (
        f'<meta property="og:image" content="{short_url}">'
        f'<meta name="twitter:image" content="{long_url}">'
    )

    assert thumbnail_html.extract_thumbnail_url_from_html(html) == long_url


def test_download_thumbnail_refreshes_expiring_preview_after_410(monkeypatch, tmp_path):
    stale_thumbnail_url = (
        "https://pix-cdn77.ypncdn.com/c6251/videos/demo/video.mp4/plain/"
        "rs:fit:1280:720/vts:354?hash=stale&validto=1"
    )
    fresh_thumbnail_url = (
        "https://pix-cdn77.ypncdn.com/c6251/videos/demo/video.mp4/plain/"
        "rs:fit:1280:720/vts:354?hash=fresh&validto=2"
    )
    source_url = "https://www.youporn.com/watch/42/demo-video/"
    requests = []

    def fake_get(url, headers=None):
        requests.append((url, headers))
        if url == stale_thumbnail_url:
            return SimpleNamespace(status_code=410, headers={"content-type": "text/plain"}, content=b"", text="")
        if url == source_url:
            return SimpleNamespace(
                status_code=200,
                headers={"content-type": "text/html"},
                content=b"",
                text=f'<meta property="og:image" content="{fresh_thumbnail_url}">',
            )
        if url == fresh_thumbnail_url:
            return SimpleNamespace(
                status_code=200,
                headers={"content-type": "image/jpeg"},
                content=b"image-bytes",
                text="",
            )
        raise AssertionError(f"unexpected url: {url}")

    service = _thumbnail_service_with_fake_http(monkeypatch, tmp_path, fake_get)

    file_path = service.download_thumbnail(
        video_id=42,
        thumbnail_url=stale_thumbnail_url,
        site_name="youporn",
        source_url=source_url,
    )

    assert file_path == str(tmp_path / "batch_001" / "42.jpg")
    assert [item[0] for item in requests] == [
        stale_thumbnail_url,
        source_url,
        fresh_thumbnail_url,
    ]


def test_download_thumbnail_refreshes_expiring_preview_after_410_for_pornhub(monkeypatch, tmp_path):
    stale_thumbnail_url = (
        "https://pix-cdn77.ypncdn.com/c6251/videos/demo/video.mp4/plain/"
        "rs:fit:1280:720/vts:354?hash=stale&validto=1"
    )
    fresh_thumbnail_url = (
        "https://ei.phncdn.com/videos/demo/fresh-thumb.jpg?validto=2"
    )
    source_url = "https://www.pornhub.com/view_video.php?viewkey=demo"
    requests = []

    def fake_get(url, headers=None):
        requests.append((url, headers))
        if url == stale_thumbnail_url:
            return SimpleNamespace(status_code=410, headers={"content-type": "text/plain"}, content=b"", text="")
        if url == source_url:
            return SimpleNamespace(
                status_code=200,
                headers={"content-type": "text/html"},
                content=b"",
                text=f'<meta property="og:image" content="{fresh_thumbnail_url}">',
            )
        if url == fresh_thumbnail_url:
            return SimpleNamespace(
                status_code=200,
                headers={"content-type": "image/jpeg"},
                content=b"image-bytes",
                text="",
            )
        raise AssertionError(f"unexpected url: {url}")

    service = _thumbnail_service_with_fake_http(monkeypatch, tmp_path, fake_get)

    file_path = service.download_thumbnail(
        video_id=88,
        thumbnail_url=stale_thumbnail_url,
        site_name="pornhub",
        source_url=source_url,
    )

    assert file_path == str(tmp_path / "batch_001" / "88.jpg")
    assert [item[0] for item in requests] == [
        stale_thumbnail_url,
        source_url,
        fresh_thumbnail_url,
    ]


def test_download_thumbnail_refreshes_pornhub_ei_video_thumb_after_410(monkeypatch, tmp_path):
    stale_thumbnail_url = "https://ei.phncdn.com/videos/202506/07/469932995/original/(m=qO7TGL0beaAaGwObaaaa)(mh=demo)0.jpg"
    fresh_thumbnail_url = (
        "https://pix-egi.phncdn.com/c6251/videos/demo/original.jpg/plain/"
        "rs:fit:350:196?validfrom=1751342400&validto=4891363200&hash=fresh"
    )
    source_url = "https://www.pornhub.com/view_video.php?viewkey=demo"
    requests = []

    def fake_get(url, headers=None):
        requests.append((url, headers))
        if url == stale_thumbnail_url:
            return SimpleNamespace(status_code=410, headers={"content-type": "text/plain"}, content=b"", text="")
        if url == source_url:
            return SimpleNamespace(
                status_code=200,
                headers={"content-type": "text/html"},
                content=b"",
                text=f'<meta name="twitter:image" content="{fresh_thumbnail_url}">',
            )
        if url == fresh_thumbnail_url:
            return SimpleNamespace(
                status_code=200,
                headers={"content-type": "image/jpeg"},
                content=b"image-bytes",
                text="",
            )
        raise AssertionError(f"unexpected url: {url}")

    service = _thumbnail_service_with_fake_http(monkeypatch, tmp_path, fake_get)

    file_path = service.download_thumbnail(
        video_id=90,
        thumbnail_url=stale_thumbnail_url,
        site_name="pornhub",
        source_url=source_url,
    )

    assert file_path == str(tmp_path / "batch_001" / "90.jpg")
    assert [item[0] for item in requests] == [
        stale_thumbnail_url,
        source_url,
        fresh_thumbnail_url,
    ]


def test_download_thumbnail_refreshes_pornhub_hdnea_preview_after_472(monkeypatch, tmp_path):
    stale_thumbnail_url = (
        "https://pix-fl.phncdn.com/videos/demo/plain/"
        "rs:fit:640:360?hdnea=expired"
    )
    fresh_thumbnail_url = "https://ei.phncdn.com/videos/demo/fresh-thumb.jpg"
    source_url = "https://www.pornhub.com/view_video.php?viewkey=demo"
    requests = []

    def fake_get(url, headers=None):
        requests.append((url, headers))
        if url == stale_thumbnail_url:
            return SimpleNamespace(status_code=472, headers={"content-type": "text/plain"}, content=b"", text="")
        if url == source_url:
            return SimpleNamespace(
                status_code=200,
                headers={"content-type": "text/html"},
                content=b"",
                text=f'<meta property="og:image" content="{fresh_thumbnail_url}">',
            )
        if url == fresh_thumbnail_url:
            return SimpleNamespace(
                status_code=200,
                headers={"content-type": "image/jpeg"},
                content=b"image-bytes",
                text="",
            )
        raise AssertionError(f"unexpected url: {url}")

    service = _thumbnail_service_with_fake_http(monkeypatch, tmp_path, fake_get)

    file_path = service.download_thumbnail(
        video_id=89,
        thumbnail_url=stale_thumbnail_url,
        site_name="pornhub",
        source_url=source_url,
    )

    assert file_path == str(tmp_path / "batch_001" / "89.jpg")
    assert [item[0] for item in requests] == [
        stale_thumbnail_url,
        source_url,
        fresh_thumbnail_url,
    ]


def test_build_request_headers_uses_source_url_cookies_and_age_gate_defaults(monkeypatch):
    site_config = ThumbnailSiteConfig()
    service = ThumbnailDownloaderService(site_config=site_config)

    monkeypatch.setattr(
        site_config,
        "get_effective_catalog",
        lambda: {
            "pornhub": {
                "http": {
                    "headers": {
                        "User-Agent": "UA",
                        "Referer": "https://www.pornhub.com",
                    },
                },
                "metadata": {
                    "requires_cookies": True,
                },
            },
        },
        raising=False,
    )
    monkeypatch.setattr(
        thumbnail_headers,
        "filter_cookies_to_query_string",
        lambda url: "sessid=abc123",
    )

    headers = service.build_request_headers(
        "pornhub",
        source_url="https://www.pornhub.com/view_video.php?viewkey=demo",
        target_url="https://ei.phncdn.com/videos/demo.jpg",
    )

    assert headers["Referer"] == "https://www.pornhub.com/view_video.php?viewkey=demo"
    assert headers["Origin"] == "https://www.pornhub.com"
    assert headers["User-Agent"] == "UA"
    assert headers["Cookie"] == (
        "sessid=abc123; age_verified=1; accessAgeDisclaimerPH=1; "
        "accessAgeDisclaimerUK=1; accessPH=1"
    )
