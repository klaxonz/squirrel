import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from services.extraction.video_persistence import VideoPersistenceService


def test_create_subscription_link_refreshes_feed_for_incremental_sync(monkeypatch):
    calls = []

    def fake_create_subscription_video(subscription_id, video_id, *, refresh_feed):
        calls.append((subscription_id, video_id, refresh_feed))
        return object(), True

    monkeypatch.setattr(
        "services.extraction.video_persistence.subscription_video_service.create_subscription_video",
        fake_create_subscription_video,
    )

    VideoPersistenceService()._create_subscription_link(
        session=object(),
        subscription_id=10,
        video_id=20,
        is_new_video=True,
        subscription_sync_mode="incremental",
    )

    assert calls == [(10, 20, True)]


def test_create_subscription_link_skips_feed_refresh_for_full_sync(monkeypatch):
    calls = []

    def fake_create_subscription_video(subscription_id, video_id, *, refresh_feed):
        calls.append((subscription_id, video_id, refresh_feed))
        return object(), True

    monkeypatch.setattr(
        "services.extraction.video_persistence.subscription_video_service.create_subscription_video",
        fake_create_subscription_video,
    )

    VideoPersistenceService()._create_subscription_link(
        session=object(),
        subscription_id=10,
        video_id=20,
        is_new_video=True,
        subscription_sync_mode="full",
    )

    assert calls == [(10, 20, False)]
