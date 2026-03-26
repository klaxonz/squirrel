from contextlib import contextmanager
from datetime import datetime, timedelta
from pathlib import Path
import sys

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from models import Base
from models.links import SubscriptionVideo, UserSubscription
from models.subscription import Subscription
from models.video import Video
from models.video_history import VideoHistory
from services import video_history_service


@contextmanager
def _managed_session(engine):
    session = Session(engine, expire_on_commit=False)
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def _seed_history(engine, histories):
    with Session(engine, expire_on_commit=False) as session:
        for item in histories:
            video = Video(
                id=item['video_id'],
                title=item.get('title', f"Video {item['video_id']}"),
                url=item.get('url', f"https://{item['domain']}/watch/{item['video_id']}"),
                domain=item['domain'],
                duration=item.get('duration', 120),
                thumbnail=item.get('thumbnail', f"https://img.example.com/{item['video_id']}.jpg"),
                publish_date=item.get('publish_date', datetime(2024, 1, 1)),
                created_at=item.get('video_created_at', datetime(2024, 1, 1)),
                updated_at=item.get('video_updated_at', datetime(2024, 1, 1)),
                is_deleted=False,
            )
            history = VideoHistory(
                user_id=item.get('user_id', 1),
                video_id=item['video_id'],
                start_time=item['end_time'] - timedelta(minutes=10),
                end_time=item['end_time'],
                duration=item.get('history_duration', 0),
                watch_duration=item.get('watch_duration', 0),
                last_position=item.get('last_position', 0),
                created_at=item.get('history_created_at', item['end_time']),
                updated_at=item.get('history_updated_at', item['end_time']),
            )
            session.add(video)
            session.add(history)

        session.commit()


def _setup_test_env(monkeypatch):
    engine = create_engine('sqlite:///:memory:')
    Base.metadata.create_all(
        engine,
        tables=[
            Video.__table__,
            VideoHistory.__table__,
            Subscription.__table__,
            SubscriptionVideo.__table__,
            UserSubscription.__table__,
        ],
    )

    monkeypatch.setattr(video_history_service, 'get_session', lambda: _managed_session(engine))
    monkeypatch.setattr(
        video_history_service.thumbnail_downloader_service,
        'get_thumbnail_url',
        lambda video_id, remote_url, video_url=None: remote_url,
    )
    monkeypatch.setattr(
        video_history_service,
        'get_site_from_url',
        lambda url: 'match' if 'match.test' in url else 'other',
    )
    monkeypatch.setattr(
        video_history_service.SiteCatalog,
        'resolve_domains',
        lambda key: ['match.test'] if key == 'match' else [],
    )

    return engine


def test_list_histories_returns_filtered_total_instead_of_current_page_size(monkeypatch):
    engine = _setup_test_env(monkeypatch)
    _seed_history(
        engine,
        [
            {'video_id': 1, 'domain': 'alpha.example.com', 'end_time': datetime(2024, 1, 3, 12, 0, 0)},
            {'video_id': 2, 'domain': 'beta.example.com', 'end_time': datetime(2024, 1, 2, 12, 0, 0)},
            {'video_id': 3, 'domain': 'gamma.example.com', 'end_time': datetime(2024, 1, 1, 12, 0, 0)},
        ],
    )

    result = video_history_service.list_histories(user_id=1, filters={}, page=1, page_size=2)

    assert len(result['items']) == 2
    assert result['total'] == 3


def test_list_histories_applies_site_filter_before_pagination(monkeypatch):
    engine = _setup_test_env(monkeypatch)
    _seed_history(
        engine,
        [
            {'video_id': 1, 'domain': 'other.test', 'url': 'https://other.test/watch/1', 'end_time': datetime(2024, 1, 3, 12, 0, 0)},
            {'video_id': 2, 'domain': 'match.test', 'url': 'https://match.test/watch/2', 'end_time': datetime(2024, 1, 2, 12, 0, 0)},
        ],
    )

    result = video_history_service.list_histories(
        user_id=1,
        filters={'site': 'match'},
        page=1,
        page_size=1,
    )

    assert result['total'] == 1
    assert [item['id'] for item in result['items']] == [2]
