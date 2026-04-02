from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
import sys

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from models import Base
from models.links import UserSubscription
from models.subscription import Subscription
from models.subscription_sync_run_projection import SubscriptionSyncRunProjection
from models.subscription_sync_subscription_projection import SubscriptionSyncSubscriptionProjection
from services import subscription_sync_center_service, subscription_sync_history_service
from utils.site_catalog import SiteCatalog


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


def _setup_test_env(monkeypatch):
    engine = create_engine('sqlite:///:memory:')
    Base.metadata.create_all(
        engine,
        tables=[
            Subscription.__table__,
            UserSubscription.__table__,
            SubscriptionSyncRunProjection.__table__,
            SubscriptionSyncSubscriptionProjection.__table__,
        ],
    )

    monkeypatch.setattr(subscription_sync_history_service, 'get_session', lambda: _managed_session(engine))
    monkeypatch.setattr(subscription_sync_center_service, 'get_session', lambda: _managed_session(engine))
    monkeypatch.setattr(
        SiteCatalog,
        'resolve_domains',
        classmethod(lambda cls, key: ['youtube.com', 'youtu.be'] if key == 'youtube' else []),
    )
    monkeypatch.setattr(
        SiteCatalog,
        'find_site_by_domain',
        classmethod(lambda cls, domain: ('youtube', {}) if domain == 'youtube.com' else (None, None)),
    )
    return engine


def _seed_sync_projection(engine):
    with Session(engine, expire_on_commit=False) as session:
        subscription = Subscription(
            id=1,
            type='CHANNEL',
            name='YouTube Channel',
            url='https://www.youtube.com/channel/demo',
            avatar=None,
            description=None,
            total_videos=0,
            is_deleted=False,
            extra_data={},
            created_at=datetime(2024, 1, 1),
            updated_at=datetime(2024, 1, 1),
        )
        session.add(subscription)
        session.add(
            UserSubscription(
                id=1,
                user_id=1,
                subscription_id=1,
                is_deleted=False,
                is_nsfw=False,
                created_at=datetime(2024, 1, 1),
                updated_at=datetime(2024, 1, 1),
            )
        )
        session.add(
            SubscriptionSyncRunProjection(
                run_id='run-1',
                subscription_id=1,
                sync_state_id=1,
                site='youtube.com',
                sync_mode='incremental',
                trigger='manual',
                request_id='req-1',
                trace_id='trace-1',
                status='success',
                current_phase='completed',
                queued_at=datetime(2024, 1, 1, 1, 0, 0),
                started_at=datetime(2024, 1, 1, 1, 1, 0),
                finished_at=datetime(2024, 1, 1, 1, 2, 0),
                duration_ms=60000,
                failure_count=0,
                error_type=None,
                error_message=None,
                videos_found=3,
                videos_enqueued=2,
                videos_extracted=2,
                videos_skipped=1,
                pending_video_count=0,
                last_event_seq_no=4,
                last_event_at=datetime(2024, 1, 1, 1, 2, 0),
                created_at=datetime(2024, 1, 1, 1, 0, 0),
                updated_at=datetime(2024, 1, 1, 1, 2, 0),
            )
        )
        session.add(
            SubscriptionSyncSubscriptionProjection(
                subscription_id=1,
                latest_run_id='run-1',
                current_status='success',
                current_phase='completed',
                last_sync_at=datetime(2024, 1, 1, 1, 2, 0),
                last_success_at=datetime(2024, 1, 1, 1, 2, 0),
                next_sync_at=datetime(2024, 1, 1, 2, 0, 0),
                last_error_message=None,
                pending_video_count=0,
                failure_streak=0,
                last_event_seq_no=4,
                updated_at=datetime(2024, 1, 1, 1, 2, 0),
            )
        )
        session.commit()


def test_list_runs_accepts_site_slug_when_projection_stores_domain(monkeypatch):
    engine = _setup_test_env(monkeypatch)
    _seed_sync_projection(engine)

    result = subscription_sync_history_service.list_runs(user_id=1, site='youtube', page=1, page_size=20)

    assert result['total'] == 1
    assert [item['site'] for item in result['data']] == ['youtube.com']


def test_list_sync_center_items_accepts_site_slug_when_projection_stores_domain(monkeypatch):
    engine = _setup_test_env(monkeypatch)
    _seed_sync_projection(engine)

    result = subscription_sync_center_service.list_sync_center_items(
        user_id=1,
        status='recent',
        site='youtube',
        query=None,
        page=1,
        page_size=20,
    )

    assert result.total == 1
    assert [item.site for item in result.data] == ['youtube.com']
