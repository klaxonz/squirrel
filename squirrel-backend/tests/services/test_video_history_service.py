from contextlib import contextmanager
from datetime import datetime, timedelta
from pathlib import Path
import sys

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from models import Base
from models.links import SubscriptionVideo, UserSubscription
from models.subscription import Subscription
from models.video import Video
from models.video_history import VideoHistory
from schemas.video_history import HistoryCreate
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
        seen_video_ids = set()
        for item in histories:
            if item['video_id'] not in seen_video_ids:
                seen_video_ids.add(item['video_id'])
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
                session.add(video)
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
            session.add(history)

        session.commit()


def _seed_subscription_links(engine, items):
    with Session(engine, expire_on_commit=False) as session:
        for item in items:
            subscription = Subscription(
                id=item['subscription_id'],
                type=item.get('type', 'CHANNEL'),
                name=item['subscription_name'],
                url=item.get('subscription_url', f"https://sub.example.com/{item['subscription_id']}"),
                avatar=item.get('subscription_avatar'),
                is_deleted=False,
            )
            session.merge(subscription)

            session.merge(
                SubscriptionVideo(
                    subscription_id=item['subscription_id'],
                    video_id=item['video_id'],
                )
            )
            session.merge(
                UserSubscription(
                    id=item.get('user_subscription_id', item['subscription_id']),
                    user_id=item.get('user_id', 1),
                    subscription_id=item['subscription_id'],
                    is_deleted=False,
                    is_nsfw=item.get('is_nsfw', False),
                )
            )

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
    with engine.begin() as connection:
        connection.execute(text('DROP INDEX ux_video_history_user_video'))

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


def test_list_histories_deduplicates_same_video_id(monkeypatch):
    engine = _setup_test_env(monkeypatch)
    _seed_history(
        engine,
        [
            {'video_id': 1, 'domain': 'alpha.example.com', 'end_time': datetime(2024, 1, 3, 12, 0, 0), 'last_position': 30},
            {'video_id': 1, 'domain': 'alpha.example.com', 'end_time': datetime(2024, 1, 2, 12, 0, 0), 'last_position': 10},
            {'video_id': 2, 'domain': 'beta.example.com', 'end_time': datetime(2024, 1, 1, 12, 0, 0), 'last_position': 20},
        ],
    )

    result = video_history_service.list_histories(user_id=1, filters={}, page=1, page_size=10)

    assert result['total'] == 2
    assert [item['id'] for item in result['items']] == [1, 2]
    assert result['items'][0]['last_position'] == 30


def test_list_histories_returns_latest_history_id(monkeypatch):
    engine = _setup_test_env(monkeypatch)
    latest_end_time = datetime(2024, 1, 3, 12, 0, 0)
    _seed_history(
        engine,
        [
            {'video_id': 1, 'domain': 'alpha.example.com', 'end_time': latest_end_time, 'last_position': 30},
            {'video_id': 1, 'domain': 'alpha.example.com', 'end_time': datetime(2024, 1, 2, 12, 0, 0), 'last_position': 10},
        ],
    )

    with Session(engine, expire_on_commit=False) as session:
        latest_history = session.query(VideoHistory).filter_by(user_id=1, video_id=1, end_time=latest_end_time).one()

    result = video_history_service.list_histories(user_id=1, filters={}, page=1, page_size=10)

    assert result['items'][0]['id'] == 1
    assert result['items'][0]['history_id'] == latest_history.id


def test_list_histories_exposes_played_at_from_history_end_time(monkeypatch):
    engine = _setup_test_env(monkeypatch)
    latest_end_time = datetime(2024, 1, 3, 12, 0, 0)
    _seed_history(
        engine,
        [
            {
                'video_id': 1,
                'domain': 'alpha.example.com',
                'end_time': latest_end_time,
                'video_created_at': datetime(2023, 12, 1, 8, 0, 0),
            },
        ],
    )

    result = video_history_service.list_histories(user_id=1, filters={}, page=1, page_size=10)

    assert result['items'][0]['played_at'] == '2024-01-03 12:00:00'
    assert result['items'][0]['created_at'] == '2023-12-01 08:00:00'


def test_list_histories_filters_date_range_by_played_at(monkeypatch):
    engine = _setup_test_env(monkeypatch)
    _seed_history(
        engine,
        [
            {
                'video_id': 1,
                'domain': 'alpha.example.com',
                'end_time': datetime(2024, 1, 3, 12, 0, 0),
                'history_created_at': datetime(2024, 1, 1, 8, 0, 0),
            },
            {
                'video_id': 2,
                'domain': 'beta.example.com',
                'end_time': datetime(2024, 1, 1, 12, 0, 0),
                'history_created_at': datetime(2024, 1, 4, 8, 0, 0),
            },
        ],
    )

    result = video_history_service.list_histories(
        user_id=1,
        filters={
            'start_date': datetime(2024, 1, 2, 0, 0, 0),
            'end_date': datetime(2024, 1, 3, 23, 59, 59),
        },
        page=1,
        page_size=10,
    )

    assert result['total'] == 1
    assert [item['id'] for item in result['items']] == [1]


def test_list_histories_filters_by_video_title_query(monkeypatch):
    engine = _setup_test_env(monkeypatch)
    _seed_history(
        engine,
        [
            {'video_id': 1, 'domain': 'alpha.example.com', 'title': 'Daily Coding Notes', 'end_time': datetime(2024, 1, 3, 12, 0, 0)},
            {'video_id': 2, 'domain': 'beta.example.com', 'title': 'Weekend Travel Log', 'end_time': datetime(2024, 1, 2, 12, 0, 0)},
        ],
    )

    result = video_history_service.list_histories(
        user_id=1,
        filters={'query': 'coding'},
        page=1,
        page_size=10,
    )

    assert result['total'] == 1
    assert [item['id'] for item in result['items']] == [1]


def test_delete_history_removes_only_target_history_for_current_user(monkeypatch):
    engine = _setup_test_env(monkeypatch)
    _seed_history(
        engine,
        [
            {'video_id': 1, 'domain': 'alpha.example.com', 'end_time': datetime(2024, 1, 3, 12, 0, 0), 'user_id': 1},
            {'video_id': 2, 'domain': 'beta.example.com', 'end_time': datetime(2024, 1, 2, 12, 0, 0), 'user_id': 1},
            {'video_id': 3, 'domain': 'gamma.example.com', 'end_time': datetime(2024, 1, 1, 12, 0, 0), 'user_id': 2},
        ],
    )

    with Session(engine, expire_on_commit=False) as session:
        target_history = session.query(VideoHistory).filter_by(user_id=1, video_id=1).one()
        other_user_history = session.query(VideoHistory).filter_by(user_id=2, video_id=3).one()

    deleted_count = video_history_service.delete_history(user_id=1, history_id=target_history.id)

    with Session(engine, expire_on_commit=False) as session:
        remaining_histories = session.query(VideoHistory).order_by(VideoHistory.id.asc()).all()

    assert deleted_count == 1
    assert [history.video_id for history in remaining_histories] == [2, 3]
    assert remaining_histories[1].id == other_user_history.id


def test_list_histories_filters_by_subscription_name_query(monkeypatch):
    engine = _setup_test_env(monkeypatch)
    _seed_history(
        engine,
        [
            {'video_id': 1, 'domain': 'alpha.example.com', 'title': 'Episode One', 'end_time': datetime(2024, 1, 3, 12, 0, 0)},
            {'video_id': 2, 'domain': 'beta.example.com', 'title': 'Episode Two', 'end_time': datetime(2024, 1, 2, 12, 0, 0)},
        ],
    )
    _seed_subscription_links(
        engine,
        [
            {'subscription_id': 101, 'subscription_name': 'Search Match Channel', 'video_id': 1, 'user_id': 1},
            {'subscription_id': 102, 'subscription_name': 'Another Channel', 'video_id': 2, 'user_id': 1},
        ],
    )

    result = video_history_service.list_histories(
        user_id=1,
        filters={'query': 'match'},
        page=1,
        page_size=1,
    )

    assert result['total'] == 1
    assert [item['id'] for item in result['items']] == [1]


def test_update_history_merges_duplicate_rows_for_same_video(monkeypatch):
    engine = _setup_test_env(monkeypatch)
    _seed_history(
        engine,
        [
            {'video_id': 1, 'domain': 'alpha.example.com', 'end_time': datetime(2024, 1, 3, 12, 0, 0), 'last_position': 30},
            {'video_id': 1, 'domain': 'alpha.example.com', 'end_time': datetime(2024, 1, 2, 12, 0, 0), 'last_position': 10},
        ],
    )

    video_history_service.update_history(
        user_id=1,
        data=HistoryCreate(video_id=1, last_position=88),
    )

    with Session(engine, expire_on_commit=False) as session:
        histories = session.query(VideoHistory).filter_by(user_id=1, video_id=1).order_by(VideoHistory.id.asc()).all()

    assert len(histories) == 1
    assert histories[0].last_position == 88


def test_batch_update_histories_updates_existing_rows_and_creates_missing_rows(monkeypatch):
    engine = _setup_test_env(monkeypatch)
    _seed_history(
        engine,
        [
            {'video_id': 1, 'domain': 'alpha.example.com', 'end_time': datetime(2024, 1, 3, 12, 0, 0), 'last_position': 30},
            {'video_id': 1, 'domain': 'alpha.example.com', 'end_time': datetime(2024, 1, 2, 12, 0, 0), 'last_position': 10},
        ],
    )
    with Session(engine, expire_on_commit=False) as session:
        session.add(
            Video(
                id=2,
                title='Video 2',
                url='https://beta.example.com/watch/2',
                domain='beta.example.com',
                duration=120,
                thumbnail='https://img.example.com/2.jpg',
                publish_date=datetime(2024, 1, 1),
                created_at=datetime(2024, 1, 1),
                updated_at=datetime(2024, 1, 1),
                is_deleted=False,
            )
        )
        session.commit()

    video_history_service.batch_update_histories(
        user_id=1,
        reports=[
            HistoryCreate(video_id=1, last_position=88),
            HistoryCreate(video_id=2, last_position=12.5),
            HistoryCreate(video_id=1, last_position=91),
        ],
    )

    with Session(engine, expire_on_commit=False) as session:
        histories = session.query(VideoHistory).filter_by(user_id=1).order_by(VideoHistory.video_id.asc(), VideoHistory.id.asc()).all()

    assert len(histories) == 2
    assert histories[0].video_id == 1
    assert histories[0].last_position == 91
    assert histories[1].video_id == 2
    assert histories[1].last_position == 12.5
