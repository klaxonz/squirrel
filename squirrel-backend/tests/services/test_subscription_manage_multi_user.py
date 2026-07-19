from contextlib import contextmanager

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from domains.subscription.application.services.core.crud import SubscriptionCrudService
from domains.subscription.application.services.core.manage import SubscriptionManageService
from domains.subscription.application.services.core.sync.lifecycle import SubscriptionSyncLifecycle
from domains.subscription.domain.junctions.user_subscription import UserSubscription
from domains.subscription.domain.models.subscription import Subscription
from domains.subscription.domain.models.subscription_sync_state import SubscriptionSyncState
from domains.user.domain.models.user import User
from infrastructure.config.settings import settings
from infrastructure.database.base import Base


def test_unsubscribe_only_deactivates_global_subscription_for_last_user(monkeypatch):
    engine = create_engine('sqlite:///:memory:')
    Base.metadata.create_all(
        engine,
        tables=[User.__table__, Subscription.__table__, UserSubscription.__table__],
    )

    @contextmanager
    def session_factory():
        session = Session(engine, expire_on_commit=False)
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    deactivated = []
    lifecycle = type(
        'Lifecycle',
        (),
        {
            'deactivate_subscription_syncs': staticmethod(
                lambda subscription_id, **kwargs: deactivated.append((subscription_id, kwargs)),
            ),
        },
    )()
    monkeypatch.setattr(settings.meili, 'url', '')

    with session_factory() as session:
        session.add_all([User(id=1, nickname='one'), User(id=2, nickname='two')])
        session.add(Subscription(id=10, type='CHANNEL', name='shared', url='https://example.com/shared'))
        session.add_all(
            [
                UserSubscription(user_id=1, subscription_id=10),
                UserSubscription(user_id=2, subscription_id=10),
            ],
        )

    service = SubscriptionManageService(session_factory=session_factory, lifecycle=lifecycle)
    crud_service = SubscriptionCrudService(session_factory=session_factory)
    assert service.unsubscribe_by_id(1, 10) is True

    with session_factory() as session:
        subscription = session.get(Subscription, 10)
        links = session.scalars(
            select(UserSubscription).where(UserSubscription.subscription_id == 10).order_by(UserSubscription.user_id),
        ).all()
    assert subscription.is_deleted is False
    assert [link.is_deleted for link in links] == [True, False]
    assert deactivated == []
    assert crud_service.check_subscription_status(1, 'https://example.com/shared')['is_subscribed'] is False
    assert crud_service.check_subscription_status(2, 'https://example.com/shared')['is_subscribed'] is True

    assert service.unsubscribe_by_id(2, 10) is True
    with session_factory() as session:
        subscription = session.get(Subscription, 10)
    assert subscription.is_deleted is True
    assert deactivated == [(10, {'reason': 'manual_unsubscribe'})]


def test_sync_deactivation_rechecks_subscription_after_concurrent_restore():
    engine = create_engine('sqlite:///:memory:')
    Base.metadata.create_all(
        engine,
        tables=[User.__table__, Subscription.__table__, UserSubscription.__table__, SubscriptionSyncState.__table__],
    )

    @contextmanager
    def session_factory():
        session = Session(engine, expire_on_commit=False)
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    with session_factory() as session:
        session.add(User(id=1, nickname='one'))
        session.add(
            Subscription(id=10, type='CHANNEL', name='restored', url='https://example.com/restored'),
        )
        session.add(UserSubscription(user_id=1, subscription_id=10, is_deleted=False))
        session.add(
            SubscriptionSyncState(
                id=20,
                subscription_id=10,
                site='example.com',
                sync_mode='incremental',
                sync_status='running',
            ),
        )

    SubscriptionSyncLifecycle(session_factory=session_factory).deactivate_subscription_syncs(
        10,
        reason='stale_unsubscribe_callback',
    )

    with session_factory() as session:
        state = session.get(SubscriptionSyncState, 20)
    assert state.sync_status == 'running'
