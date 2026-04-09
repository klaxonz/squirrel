from pathlib import Path
import sys
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from core.extraction.services import thumbnail_downloader
from core.extraction.services.thumbnail_downloader import ThumbnailDownloaderService


def test_bulk_thumbnail_lookup_uses_direct_local_file_check(monkeypatch):
    service = ThumbnailDownloaderService()
    batch_calls = []

    monkeypatch.setattr(thumbnail_downloader, 'get_site_from_url', lambda video_url: 'youtube')
    monkeypatch.setattr(service, '_should_use_offline', lambda site_name: True)
    monkeypatch.setattr(service, '_get_batch_dir', lambda video_id: '/tmp/batch-1')
    monkeypatch.setattr(service, '_get_extension', lambda remote_url: '.jpg')
    monkeypatch.setattr(service, '_get_local_thumbnail_path_map', lambda indexed_items: {}, raising=False)
    monkeypatch.setattr(
        service,
        '_get_batch_index',
        lambda batch_dir: batch_calls.append(batch_dir) or {11: '11.jpg'},
    )
    monkeypatch.setattr(
        thumbnail_downloader.os.path,
        'exists',
        lambda path: path.replace('\\', '/') == '/tmp/batch-1/11.jpg',
    )

    results = service.get_thumbnail_url_map([
        (11, 'https://img.example.com/11.jpg', 'https://www.youtube.com/watch?v=11'),
        (12, 'https://img.example.com/12.jpg', 'https://www.youtube.com/watch?v=12'),
    ])

    assert batch_calls == []
    assert results == {
        11: '/static/thumbnails/batch-1/11.jpg',
        12: 'https://img.example.com/12.jpg',
    }


def test_bulk_thumbnail_lookup_prefers_local_index(monkeypatch):
    service = ThumbnailDownloaderService()
    fallback_calls = []

    monkeypatch.setattr(thumbnail_downloader, 'get_site_from_url', lambda video_url: 'youtube')
    monkeypatch.setattr(service, '_should_use_offline', lambda site_name: True)
    monkeypatch.setattr(
        service,
        '_get_local_thumbnail_path_map',
        lambda indexed_items: {
            21: '/static/thumbnails/batch_001/21.webp',
        },
        raising=False,
    )
    monkeypatch.setattr(
        service,
        '_get_local_thumbnail_path',
        lambda video_id, remote_url=None: fallback_calls.append((video_id, remote_url)) or None,
    )

    results = service.get_thumbnail_url_map([
        (21, 'https://img.example.com/21.webp', 'https://www.youtube.com/watch?v=21'),
        (22, 'https://img.example.com/22.webp', 'https://www.youtube.com/watch?v=22'),
    ])

    assert results == {
        21: '/static/thumbnails/batch_001/21.webp',
        22: 'https://img.example.com/22.webp',
    }
    assert fallback_calls == [
        (22, 'https://img.example.com/22.webp'),
    ]


def test_download_thumbnail_updates_local_index(monkeypatch, tmp_path):
    service = ThumbnailDownloaderService()
    index_updates = []

    monkeypatch.setattr(service, '_should_download', lambda site_name: True)
    monkeypatch.setattr(service, '_get_batch_dir', lambda video_id: str(tmp_path / 'batch_001'))
    monkeypatch.setattr(service, '_get_extension', lambda remote_url: '.jpg')
    monkeypatch.setattr(
        service,
        '_upsert_local_thumbnail_index',
        lambda video_id, batch_name, filename, exists=True: index_updates.append(
            (video_id, batch_name, filename, exists)
        ),
        raising=False,
    )
    monkeypatch.setattr(
        thumbnail_downloader.os.path,
        'exists',
        lambda path: False,
    )
    monkeypatch.setattr(
        service,
        '_get_http_client',
        lambda: SimpleNamespace(
            get=lambda url, headers=None: SimpleNamespace(
                status_code=200,
                headers={'content-type': 'image/jpeg'},
                content=b'image-bytes',
            )
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


def test_build_request_headers_uses_source_url_cookies_and_age_gate_defaults(monkeypatch):
    service = ThumbnailDownloaderService()

    monkeypatch.setattr(
        service,
        '_get_effective_catalog',
        lambda: {
            'pornhub': {
                'http': {
                    'headers': {
                        'User-Agent': 'UA',
                        'Referer': 'https://www.pornhub.com',
                    },
                },
                'metadata': {
                    'requires_cookies': True,
                },
            }
        },
        raising=False,
    )
    monkeypatch.setattr(
        thumbnail_downloader,
        'filter_cookies_to_query_string',
        lambda url: 'sessid=abc123',
    )

    headers = service.build_request_headers(
        'pornhub',
        source_url='https://www.pornhub.com/view_video.php?viewkey=demo',
        target_url='https://ei.phncdn.com/videos/demo.jpg',
    )

    assert headers['Referer'] == 'https://www.pornhub.com/view_video.php?viewkey=demo'
    assert headers['Origin'] == 'https://www.pornhub.com'
    assert headers['User-Agent'] == 'UA'
    assert headers['Cookie'] == (
        'sessid=abc123; age_verified=1; accessAgeDisclaimerPH=1; '
        'accessAgeDisclaimerUK=1; accessPH=1'
    )
