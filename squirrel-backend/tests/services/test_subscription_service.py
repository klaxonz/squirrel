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
from models.subscription_sync_state import SubscriptionSyncState
from services import subscription_service
from services import subscription_sync_state_service


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
            SubscriptionSyncState.__table__,
        ],
    )

    monkeypatch.setattr(subscription_service, 'get_session', lambda: _managed_session(engine))
    monkeypatch.setattr(subscription_sync_state_service, 'get_session', lambda: _managed_session(engine))
    return engine


def _seed_subscription(engine, *, subscription_id: int = 1, user_ids: list[int] | None = None):
    user_ids = user_ids or [1]
    with Session(engine, expire_on_commit=False) as session:
        subscription = Subscription(
            id=subscription_id,
            type='CHANNEL',
            name='Test subscription',
            url=f'https://www.youtube.com/channel/{subscription_id}',
            avatar=None,
            description=None,
            total_videos=0,
            is_deleted=False,
            extra_data={},
            created_at=datetime(2024, 1, 1),
            updated_at=datetime(2024, 1, 1),
        )
        session.add(subscription)

        for index, user_id in enumerate(user_ids, start=1):
            session.add(
                UserSubscription(
                    id=index,
                    user_id=user_id,
                    subscription_id=subscription_id,
                    is_deleted=False,
                    is_nsfw=False,
                    created_at=datetime(2024, 1, 1),
                    updated_at=datetime(2024, 1, 1),
                )
            )

        session.add(
            SubscriptionSyncState(
                subscription_id=subscription_id,
                site='youtube',
                sync_mode='incremental',
                sync_status='queued',
                cursor_payload={},
                next_sync_at=datetime(2024, 1, 1, 1, 0, 0),
                queued_at=datetime(2024, 1, 1, 1, 0, 0),
                locked_at=datetime(2024, 1, 1, 1, 0, 0),
                pending_video_count=3,
                failure_count=0,
                idle_sync_count=0,
                version=0,
            )
        )
        session.commit()


def test_unsubscribe_by_id_deactivates_subscription_when_last_user_leaves(monkeypatch):
    engine = _setup_test_env(monkeypatch)
    _seed_subscription(engine, user_ids=[1])

    result = subscription_service.unsubscribe_by_id(user_id=1, subscription_id=1)

    assert result is True

    with Session(engine, expire_on_commit=False) as session:
        subscription = session.get(Subscription, 1)
        user_subscription = session.query(UserSubscription).filter_by(user_id=1, subscription_id=1).one()
        sync_state = session.query(SubscriptionSyncState).filter_by(subscription_id=1).one()

    assert user_subscription.is_deleted is True
    assert subscription.is_deleted is True
    assert sync_state.sync_status == 'idle'
    assert sync_state.queue_token is None
    assert sync_state.queued_at is None
    assert sync_state.locked_at is None
    assert sync_state.pending_video_count == 0
    assert sync_state.last_error == 'no_active_subscribers'


def test_unsubscribe_by_id_keeps_subscription_active_when_other_users_remain(monkeypatch):
    engine = _setup_test_env(monkeypatch)
    _seed_subscription(engine, user_ids=[1, 2])

    result = subscription_service.unsubscribe_by_id(user_id=1, subscription_id=1)

    assert result is True

    with Session(engine, expire_on_commit=False) as session:
        subscription = session.get(Subscription, 1)
        removed_link = session.query(UserSubscription).filter_by(user_id=1, subscription_id=1).one()
        remaining_link = session.query(UserSubscription).filter_by(user_id=2, subscription_id=1).one()
        sync_state = session.query(SubscriptionSyncState).filter_by(subscription_id=1).one()

    assert removed_link.is_deleted is True
    assert remaining_link.is_deleted is False
    assert subscription.is_deleted is False
    assert sync_state.sync_status == 'queued'
    assert sync_state.pending_video_count == 3
