from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
import sys

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from models import Base
from models.creator import Creator
from models.links import SubscriptionVideo, UserSubscription, VideoCreator
from models.subscription import ContentType, Subscription
from models.user_video_feed import UserVideoFeed
from models.video import Video
from models.video_history import VideoHistory
from services import search_suggestion_service


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


def _setup_env(monkeypatch):
    engine = create_engine('sqlite:///:memory:')
    Base.metadata.create_all(
        engine,
        tables=[
            Video.__table__,
            Subscription.__table__,
            SubscriptionVideo.__table__,
            UserSubscription.__table__,
            UserVideoFeed.__table__,
            VideoHistory.__table__,
            Creator.__table__,
            VideoCreator.__table__,
        ],
    )
    monkeypatch.setattr(search_suggestion_service, 'get_session', lambda: _managed_session(engine))
    monkeypatch.setattr(search_suggestion_service.user_config_service, 'get_config', lambda _user_id: {'showNsfw': False})
    monkeypatch.setattr(
        search_suggestion_service.SiteCatalog,
        'find_site_by_domain',
        lambda domain: ('bilibili', {'metadata': {}}) if domain == 'bilibili.com' else (None, None),
    )
    return engine


def _seed_visible_content(engine):
    with Session(engine, expire_on_commit=False) as session:
        session.add(
            Subscription(
                id=1,
                type=ContentType.CHANNEL,
                name='黑神话研究所',
                url='https://space.bilibili.com/1',
                is_deleted=False,
                created_at=datetime(2024, 1, 1),
                updated_at=datetime(2024, 1, 3),
            )
        )
        session.add(
            UserSubscription(
                id=1,
                user_id=7,
                subscription_id=1,
                is_deleted=False,
                is_nsfw=False,
                created_at=datetime(2024, 1, 1),
                updated_at=datetime(2024, 1, 3),
            )
        )
        session.add(
            Video(
                id=1,
                title='黑神话悟空 终极预告',
                url='https://www.bilibili.com/video/BV1xx',
                domain='bilibili.com',
                is_deleted=False,
                created_at=datetime(2024, 1, 2),
                publish_date=datetime(2024, 1, 2),
            )
        )
        session.add(SubscriptionVideo(subscription_id=1, video_id=1))
        session.add(
            UserVideoFeed(
                id=1,
                user_id=7,
                subscription_id=1,
                video_id=1,
                publish_date=datetime(2024, 1, 2),
                video_created_at=datetime(2024, 1, 2),
                domain='bilibili.com',
                is_nsfw=False,
                created_at=datetime(2024, 1, 2),
                updated_at=datetime(2024, 1, 2),
            )
        )
        session.add(
            Creator(
                id=1,
                name='黑神话官方',
                url='https://space.bilibili.com/100',
                is_deleted=False,
                created_at=datetime(2024, 1, 2),
                updated_at=datetime(2024, 1, 2),
            )
        )
        session.add(VideoCreator(video_id=1, creator_id=1))
        session.add(
            VideoHistory(
                id=1,
                user_id=7,
                video_id=1,
                start_time=datetime(2024, 1, 2, 12, 0, 0),
                end_time=datetime(2024, 1, 2, 12, 30, 0),
                duration=120,
                watch_duration=120,
                last_position=118,
                created_at=datetime(2024, 1, 2, 12, 0, 0),
                updated_at=datetime(2024, 1, 2, 12, 30, 0),
            )
        )
        session.commit()


def _seed_nsfw_content(engine):
    with Session(engine, expire_on_commit=False) as session:
        session.add(
            Subscription(
                id=2,
                type=ContentType.CHANNEL,
                name='秘密频道',
                url='https://secret.example.com/channel',
                is_deleted=False,
                created_at=datetime(2024, 1, 1),
                updated_at=datetime(2024, 1, 1),
            )
        )
        session.add(
            UserSubscription(
                id=2,
                user_id=7,
                subscription_id=2,
                is_deleted=False,
                is_nsfw=True,
                created_at=datetime(2024, 1, 1),
                updated_at=datetime(2024, 1, 1),
            )
        )
        session.add(
            Video(
                id=2,
                title='秘密影片预告',
                url='https://secret.example.com/video/1',
                domain='secret.example.com',
                is_deleted=False,
                created_at=datetime(2024, 1, 4),
                publish_date=datetime(2024, 1, 4),
            )
        )
        session.add(SubscriptionVideo(subscription_id=2, video_id=2))
        session.add(
            UserVideoFeed(
                id=2,
                user_id=7,
                subscription_id=2,
                video_id=2,
                publish_date=datetime(2024, 1, 4),
                video_created_at=datetime(2024, 1, 4),
                domain='secret.example.com',
                is_nsfw=True,
                created_at=datetime(2024, 1, 4),
                updated_at=datetime(2024, 1, 4),
            )
        )
        session.commit()


def test_list_search_suggestions_prioritizes_scope_specific_sources(monkeypatch):
    engine = _setup_env(monkeypatch)
    _seed_visible_content(engine)

    items = search_suggestion_service.list_search_suggestions(7, query='黑神话', scope='history', limit=5)

    assert items
    assert items[0]['type'] == 'history'
    assert items[0]['value'] == '黑神话悟空 终极预告'
    assert any(item['type'] == 'subscription' for item in items)
    assert any(item['type'] == 'creator' for item in items)


def test_list_search_suggestions_hides_nsfw_items_when_user_disabled(monkeypatch):
    engine = _setup_env(monkeypatch)
    _seed_visible_content(engine)
    _seed_nsfw_content(engine)

    items = search_suggestion_service.list_search_suggestions(7, query='秘密', scope='home', limit=5)

    assert items == []


def test_home_scope_uses_user_feed_video_suggestions(monkeypatch):
    engine = _setup_env(monkeypatch)
    _seed_visible_content(engine)

    items = search_suggestion_service.list_search_suggestions(7, query='终极', scope='home', limit=5)

    assert items
    assert items[0]['type'] == 'video'
    assert items[0]['value'] == '黑神话悟空 终极预告'
