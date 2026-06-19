import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from infrastructure.scheduling.base import TaskRegistry
from workers.scheduling.tasks import thumbnail_refresh_task
from workers.scheduling.tasks.thumbnail_refresh_task import ThumbnailRefreshTask


def test_thumbnail_refresh_task_is_registered_for_scheduler():
    assert ThumbnailRefreshTask in TaskRegistry.tasks
    assert ThumbnailRefreshTask.interval == 60 * 24
    assert ThumbnailRefreshTask.unit == 'minutes'
    assert ThumbnailRefreshTask.start_immediately is True


def test_thumbnail_refresh_task_includes_youporn_when_offline_download_enabled(monkeypatch):
    monkeypatch.setattr(
        thumbnail_refresh_task,
        'get_effective_site_catalog',
        lambda: {
            'pornhub': {
                'enabled': True,
                'metadata': {
                    'offline_thumbnails_download': False,
                },
            },
            'youporn': {
                'enabled': True,
                'metadata': {
                    'offline_thumbnails_download': True,
                },
            },
        },
    )

    assert ThumbnailRefreshTask._get_refresh_targets() == [
        ('youporn', '%youporn.com%'),
    ]


def test_thumbnail_refresh_task_uses_stored_youporn_thumbnail_without_page_fetch(monkeypatch):
    download_calls = []

    monkeypatch.setattr(
        ThumbnailRefreshTask,
        '_fetch_thumbnail_url_from_page',
        lambda video, site_name: (_ for _ in ()).throw(AssertionError('page fetch should not run')),
    )
    monkeypatch.setattr(
        thumbnail_refresh_task.thumbnail_downloader_service,
        'download_thumbnail',
        lambda video_id, thumbnail_url, site_name, source_url=None: download_calls.append(
            (video_id, thumbnail_url, site_name, source_url),
        ),
    )

    video = SimpleNamespace(
        id=42,
        url='https://www.youporn.com/watch/42/demo-video/',
        thumbnail='https://fi1-ph.ypncdn.com/videos/demo/42.jpg',
    )

    ThumbnailRefreshTask._process_single_video(video, 'youporn')

    assert download_calls == [
        (
            42,
            'https://fi1-ph.ypncdn.com/videos/demo/42.jpg',
            'youporn',
            'https://www.youporn.com/watch/42/demo-video/',
        ),
    ]


def test_thumbnail_refresh_task_falls_back_to_page_thumbnail_when_stored_url_fails(monkeypatch):
    download_calls = []

    monkeypatch.setattr(
        ThumbnailRefreshTask,
        '_fetch_thumbnail_url_from_page',
        lambda video, site_name: 'https://fi1-ph.ypncdn.com/videos/demo/fresh-42.jpg',
    )
    monkeypatch.setattr(
        thumbnail_refresh_task.thumbnail_downloader_service,
        'download_thumbnail',
        lambda video_id, thumbnail_url, site_name, source_url=None: (
            download_calls.append((video_id, thumbnail_url, site_name, source_url)),
            None if len(download_calls) == 1 else '/tmp/fresh-42.jpg',
        )[1],
    )

    video = SimpleNamespace(
        id=42,
        url='https://www.youporn.com/watch/42/demo-video/',
        thumbnail='https://fi1-ph.ypncdn.com/videos/demo/stale-42.jpg',
    )

    ThumbnailRefreshTask._process_single_video(video, 'youporn')

    assert download_calls == [
        (
            42,
            'https://fi1-ph.ypncdn.com/videos/demo/stale-42.jpg',
            'youporn',
            'https://www.youporn.com/watch/42/demo-video/',
        ),
        (
            42,
            'https://fi1-ph.ypncdn.com/videos/demo/fresh-42.jpg',
            'youporn',
            'https://www.youporn.com/watch/42/demo-video/',
        ),
    ]


def test_thumbnail_refresh_task_extracts_html_escaped_og_image():
    from domains.video.application.services.extraction.thumbnail.html import extract_thumbnail_url_from_html

    html_doc = """
    <html>
      <head>
        <meta property="og:image" content="https://cdn.example.com/thumb.jpg?hash=abc&amp;validto=123" />
      </head>
    </html>
    """

    assert extract_thumbnail_url_from_html(html_doc) == ('https://cdn.example.com/thumb.jpg?hash=abc&validto=123')
