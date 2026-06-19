from contextlib import contextmanager
from datetime import datetime, timedelta
from unittest.mock import patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from domains.subscription.domain.junctions.user_subscription import UserSubscription
from domains.subscription.domain.models.subscription import Subscription
from domains.video.application.services.history.service import VideoHistoryService
from domains.video.domain.junctions.subscription_video import SubscriptionVideo
from domains.video.domain.models.video import Video
from domains.video.domain.models.video_history import VideoHistory
from domains.video.interfaces.dto.video_history import HistoryCreate
from infrastructure.database.base import Base

pytestmark = [pytest.mark.anyio]


@pytest.fixture
def engine():
    engine = create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)
    return engine


@pytest.fixture
def session_factory(engine):
    @contextmanager
    def factory():
        session = Session(engine, expire_on_commit=False)
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    return factory


@pytest.fixture
def svc(session_factory):
    return VideoHistoryService(session_factory=session_factory, get_user_config=lambda _user_id: {'showNsfw': True})


def _seed_history(engine, histories):
    with Session(engine, expire_on_commit=False) as session:
        seen_video_ids = set()
        for item in histories:
            if item['video_id'] not in seen_video_ids:
                seen_video_ids.add(item['video_id'])
                video = Video(
                    id=item['video_id'],
                    title=item.get('title', f'Video {item["video_id"]}'),
                    url=item.get('url', f'https://{item["domain"]}/watch/{item["video_id"]}'),
                    domain=item['domain'],
                    duration=item.get('duration', 120),
                    thumbnail=item.get('thumbnail', f'https://img.example.com/{item["video_id"]}.jpg'),
                    publish_date=item.get('publish_date', datetime(2024, 1, 1)),
                    created_at=item.get('video_created_at', datetime(2024, 1, 1)),
                    updated_at=item.get('video_updated_at', datetime(2024, 1, 1)),
                    is_deleted=False,
                )
                session.add(video)
            existing = (
                session.query(VideoHistory).filter_by(user_id=item.get('user_id', 1), video_id=item['video_id']).first()
            )
            if existing:
                existing.end_time = item['end_time']
                existing.last_position = item.get('last_position', existing.last_position)
                existing.created_at = item.get('history_created_at', existing.created_at)
                existing.updated_at = item.get('history_updated_at', existing.updated_at)
            else:
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
                url=item.get('subscription_url', f'https://sub.example.com/{item["subscription_id"]}'),
                avatar=item.get('subscription_avatar'),
                is_deleted=False,
            )
            session.merge(subscription)
            link = SubscriptionVideo(
                video_id=item['video_id'],
                subscription_id=item['subscription_id'],
            )
            session.merge(link)
        session.commit()


def _seed_videos(engine, items):
    with Session(engine, expire_on_commit=False) as session:
        for item in items:
            session.add(
                Video(
                    id=item['video_id'],
                    title=item.get('title', f'Video {item["video_id"]}'),
                    url=item.get('url', f'https://{item["domain"]}/watch/{item["video_id"]}'),
                    domain=item['domain'],
                    duration=item.get('duration', 120),
                    thumbnail=item.get('thumbnail', f'https://img.example.com/{item["video_id"]}.jpg'),
                    publish_date=item.get('publish_date', datetime(2024, 1, 1)),
                    created_at=item.get('video_created_at', datetime(2024, 1, 1)),
                    updated_at=item.get('video_updated_at', datetime(2024, 1, 1)),
                    is_deleted=False,
                ),
            )
        session.commit()


def test_list_histories_returns_filtered_total_instead_of_current_page_size(engine, svc):
    _seed_history(
        engine,
        [
            {'video_id': 1, 'domain': 'example.com', 'end_time': datetime(2024, 6, 1)},
            {'video_id': 2, 'domain': 'example.com', 'end_time': datetime(2024, 6, 2)},
        ],
    )

    result = svc.list_histories(1, {}, 1, 1)

    assert result['total'] == 2
    assert len(result['items']) == 1


def test_list_histories_applies_site_filter_before_pagination(engine, svc):
    with patch('infrastructure.site_catalog.catalog.SiteCatalog.resolve_domains', return_value=['site-a.com']):
        _seed_history(
            engine,
            [
                {'video_id': 1, 'domain': 'site-a.com', 'end_time': datetime(2024, 6, 1)},
                {'video_id': 2, 'domain': 'site-b.com', 'end_time': datetime(2024, 6, 2)},
            ],
        )

        result = svc.list_histories(1, {'site': 'site-a.com'}, 1, 20)

    assert result['total'] == 1
    assert result['items'][0]['id'] == 1


def test_list_histories_hides_nsfw_results_when_show_nsfw_disabled(engine, session_factory):
    svc = VideoHistoryService(session_factory=session_factory, get_user_config=lambda _user_id: {'showNsfw': False})
    _seed_history(
        engine,
        [
            {'video_id': 1, 'domain': 'example.com', 'end_time': datetime(2024, 6, 1)},
            {'video_id': 2, 'domain': 'example.com', 'end_time': datetime(2024, 6, 2)},
        ],
    )
    _seed_subscription_links(
        engine,
        [
            {'video_id': 1, 'subscription_id': 1, 'subscription_name': 'Safe'},
            {'video_id': 2, 'subscription_id': 2, 'subscription_name': 'NSFW'},
        ],
    )

    with Session(engine, expire_on_commit=False) as session:
        session.add(UserSubscription(user_id=1, subscription_id=2, is_nsfw=True))
        session.commit()

    result = svc.list_histories(1, {'nsfw': 'no'}, 1, 20)

    assert result['total'] == 1
    assert result['items'][0]['id'] == 1


def test_list_histories_deduplicates_same_video_id(engine, svc):
    _seed_history(
        engine,
        [
            {'video_id': 1, 'domain': 'example.com', 'end_time': datetime(2024, 6, 2)},
            {'video_id': 1, 'domain': 'example.com', 'end_time': datetime(2024, 6, 1)},
        ],
    )

    result = svc.list_histories(1, {}, 1, 20)

    assert result['total'] == 1
    assert len(result['items']) == 1


def test_list_histories_returns_latest_history_id(engine, svc):
    _seed_history(
        engine,
        [
            {
                'video_id': 1,
                'domain': 'example.com',
                'end_time': datetime(2024, 6, 1),
                'history_created_at': datetime(2024, 6, 1, 12, 0),
                'history_updated_at': datetime(2024, 6, 1, 12, 0),
            },
            {
                'video_id': 1,
                'domain': 'example.com',
                'end_time': datetime(2024, 6, 2),
                'history_created_at': datetime(2024, 6, 2, 12, 0),
                'history_updated_at': datetime(2024, 6, 2, 12, 0),
            },
        ],
    )

    result = svc.list_histories(1, {}, 1, 20)

    assert result['total'] == 1
    first = result['items'][0]
    assert first['last_position'] == 0


def test_list_histories_exposes_played_at_from_history_end_time(engine, svc):
    _seed_history(
        engine,
        [
            {'video_id': 1, 'domain': 'example.com', 'end_time': datetime(2024, 6, 5, 14, 30, 0)},
        ],
    )

    result = svc.list_histories(1, {}, 1, 20)

    assert result['items'][0]['played_at'] == '2024-06-05 14:30:00'


def test_list_histories_filters_date_range_by_played_at(engine, svc):
    _seed_history(
        engine,
        [
            {'video_id': 1, 'domain': 'example.com', 'end_time': datetime(2024, 6, 1)},
            {'video_id': 2, 'domain': 'example.com', 'end_time': datetime(2024, 6, 15)},
        ],
    )

    result = svc.list_histories(1, {'start_date': datetime(2024, 6, 10), 'end_date': datetime(2024, 6, 20)}, 1, 20)

    assert result['total'] == 1
    assert result['items'][0]['id'] == 2


def test_list_histories_filters_by_video_title_query(engine, svc):
    _seed_history(
        engine,
        [
            {'video_id': 1, 'domain': 'example.com', 'title': 'Python Tutorial', 'end_time': datetime(2024, 6, 1)},
            {'video_id': 2, 'domain': 'example.com', 'title': 'Cat Video', 'end_time': datetime(2024, 6, 2)},
        ],
    )

    with patch('domains.video.application.services.history.query._recall_video_ids_for_history', return_value=[1]):
        result = svc.list_histories(1, {'query': 'tutorial'}, 1, 20)

    assert result['total'] == 1
    assert result['items'][0]['id'] == 1


def test_delete_history_removes_only_target_history_for_current_user(engine, svc):
    _seed_history(
        engine,
        [
            {'video_id': 1, 'domain': 'example.com', 'end_time': datetime(2024, 6, 1)},
            {'video_id': 2, 'domain': 'example.com', 'end_time': datetime(2024, 6, 2), 'user_id': 1},
        ],
    )

    deleted_count = svc.delete_history(1, 1)

    assert deleted_count == 1
    remaining = svc.list_histories(1, {}, 1, 20)
    assert remaining['total'] == 1
    assert remaining['items'][0]['id'] == 2


def test_list_histories_filters_by_subscription_name_query(engine, svc):
    with patch('infrastructure.site_catalog.catalog.SiteCatalog.resolve_domains', return_value=['example.com']):
        _seed_history(
            engine,
            [
                {'video_id': 1, 'domain': 'example.com', 'end_time': datetime(2024, 6, 1)},
                {'video_id': 2, 'domain': 'example.com', 'end_time': datetime(2024, 6, 2)},
            ],
        )
        _seed_subscription_links(
            engine,
            [
                {'video_id': 1, 'subscription_id': 1, 'subscription_name': 'Tech Channel'},
                {'video_id': 2, 'subscription_id': 2, 'subscription_name': 'Music Channel'},
            ],
        )
        with Session(engine, expire_on_commit=False) as session:
            session.add_all(
                [
                    UserSubscription(user_id=1, subscription_id=1, is_deleted=False, is_nsfw=False),
                    UserSubscription(user_id=1, subscription_id=2, is_deleted=False, is_nsfw=False),
                ]
            )
            session.commit()

        with patch('domains.video.application.services.history.query._recall_video_ids_for_history', return_value=[1]):
            result = svc.list_histories(1, {'query': 'tech'}, 1, 20)

    assert result['total'] == 1, f'expected 1 but got {result}'
    assert result['items'][0]['id'] == 1


def test_list_histories_supports_field_search_tokens(engine, svc):
    _seed_history(
        engine,
        [
            {'video_id': 1, 'domain': 'example.com', 'title': 'Python 101', 'end_time': datetime(2024, 6, 1)},
            {'video_id': 2, 'domain': 'example.com', 'title': 'Rust 101', 'end_time': datetime(2024, 6, 2)},
        ],
    )

    with patch('domains.video.application.services.history.query._recall_video_ids_for_history', return_value=[1]):
        result = svc.list_histories(1, {'query': 'title:python'}, 1, 20)

    assert result['total'] == 1
    assert result['items'][0]['id'] == 1


def test_update_history_merges_duplicate_rows_for_same_video(engine, svc):
    _seed_history(
        engine,
        [
            {'video_id': 1, 'domain': 'example.com', 'end_time': datetime(2024, 6, 2)},
        ],
    )

    svc.update_history(
        1, HistoryCreate(video_id=1, timestamp=int(datetime(2024, 6, 3).timestamp() * 1000), last_position=30)
    )

    result = svc.list_histories(1, {}, 1, 20)
    assert result['total'] == 1
    assert result['items'][0]['last_position'] == 30


def test_batch_update_histories_updates_existing_rows_and_creates_missing_rows(engine, svc):
    _seed_history(
        engine,
        [
            {'video_id': 1, 'domain': 'example.com', 'end_time': datetime(2024, 6, 1)},
        ],
    )

    svc.batch_update_histories(
        1,
        [
            HistoryCreate(video_id=1, timestamp=int(datetime(2024, 6, 2).timestamp() * 1000), last_position=50),
            HistoryCreate(video_id=2, timestamp=int(datetime(2024, 6, 2).timestamp() * 1000), last_position=10),
        ],
    )
    _seed_videos(
        engine,
        [
            {'video_id': 2, 'domain': 'example.com'},
        ],
    )

    result = svc.list_histories(1, {}, 1, 20)
    assert result['total'] == 2


def test_update_history_ignores_stale_timestamp_that_would_rewind_progress(engine, svc):
    _seed_history(
        engine,
        [
            {'video_id': 1, 'domain': 'example.com', 'end_time': datetime(2024, 6, 5), 'last_position': 90},
        ],
    )

    svc.update_history(
        1, HistoryCreate(video_id=1, timestamp=int(datetime(2024, 6, 3).timestamp() * 1000), last_position=10)
    )

    result = svc.list_histories(1, {}, 1, 20)
    assert result['items'][0]['last_position'] == 90


def test_batch_update_histories_prefers_latest_timestamp_per_video(engine, svc):
    _seed_history(
        engine,
        [
            {'video_id': 1, 'domain': 'example.com', 'end_time': datetime(2024, 1, 1)},
        ],
    )
    svc.batch_update_histories(
        1,
        [
            HistoryCreate(video_id=1, timestamp=int(datetime(2024, 6, 1).timestamp() * 1000), last_position=10),
            HistoryCreate(video_id=1, timestamp=int(datetime(2024, 6, 2).timestamp() * 1000), last_position=50),
        ],
    )

    result = svc.list_histories(1, {}, 1, 20)
    assert result['total'] == 1
    assert result['items'][0]['last_position'] == 50
