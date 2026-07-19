from contextlib import contextmanager
from types import SimpleNamespace

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from domains.subscription.application.services.core.import_service import SubscriptionImportService
from domains.subscription.application.services.core.runtime_models import SubscriptionImportItem
from domains.subscription.application.services.crawl.tasks.service import CrawlTaskService
from domains.subscription.domain.junctions.user_subscription import UserSubscription
from domains.subscription.domain.models.crawl_dispatch_scope import CrawlDispatchScope
from domains.subscription.domain.models.crawl_job import CrawlJob
from domains.subscription.domain.models.crawl_task import CrawlTask
from domains.subscription.domain.models.subscription import Subscription
from domains.user.domain.models.user import User
from infrastructure.database.base import Base


def test_subscription_import_is_persisted_as_durable_crawl_task():
    engine = create_engine('sqlite:///:memory:')
    Base.metadata.create_all(
        engine,
        tables=[
            User.__table__,
            Subscription.__table__,
            UserSubscription.__table__,
            CrawlJob.__table__,
            CrawlTask.__table__,
            CrawlDispatchScope.__table__,
        ],
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

    crawl_tasks = CrawlTaskService(session_factory=session_factory)
    service = SubscriptionImportService(session_factory=session_factory, crawl_tasks=crawl_tasks)
    item = SubscriptionImportItem(
        url='https://www.youtube.com/@demo',
        name='Demo',
        avatar='https://example.com/avatar.jpg',
    )

    assert service._enqueue_subscription_tasks([item], user_id=7, site_name='youtube') == 1
    assert service._enqueue_subscription_tasks([item], user_id=7, site_name='youtube') == 0

    with Session(engine, expire_on_commit=False) as session:
        jobs = session.query(CrawlJob).all()
        tasks = session.query(CrawlTask).all()
    assert len(jobs) == 1
    assert len(tasks) == 1
    assert tasks[0].task_type == 'subscription_import'
    assert tasks[0].payload['user_id'] == 7
    assert tasks[0].payload['name'] == 'Demo'


def test_delayed_import_does_not_override_newer_manual_unsubscribe():
    engine = create_engine('sqlite:///:memory:')
    Base.metadata.create_all(
        engine,
        tables=[
            User.__table__,
            Subscription.__table__,
            UserSubscription.__table__,
            CrawlJob.__table__,
            CrawlTask.__table__,
            CrawlDispatchScope.__table__,
        ],
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
        session.add(User(id=7, nickname='demo'))
        session.add(Subscription(id=9, type='CHANNEL', name='Demo', url='https://www.youtube.com/@demo'))
        session.add(
            UserSubscription(
                user_id=7,
                subscription_id=9,
                is_deleted=False,
                intent_version=0,
            ),
        )

    service = SubscriptionImportService(
        session_factory=session_factory,
        crawl_tasks=CrawlTaskService(session_factory=session_factory),
    )
    service.manage_service.lifecycle = SimpleNamespace(ensure_subscription_syncs=lambda *_args, **_kwargs: None)
    item = SubscriptionImportItem(url='https://www.youtube.com/@demo', name='Demo')
    assert service._enqueue_subscription_tasks([item], user_id=7, site_name='youtube') == 1

    with session_factory() as session:
        link = session.scalar(
            select(UserSubscription).where(
                UserSubscription.user_id == 7,
                UserSubscription.subscription_id == 9,
            ),
        )
        link.is_deleted = True
        link.intent_version += 1
        session.get(Subscription, 9).is_deleted = True

    with Session(engine, expire_on_commit=False) as session:
        task = session.scalar(select(CrawlTask).where(CrawlTask.task_type == 'subscription_import'))
        payload = dict(task.payload)
    service.process_import_payload(payload)

    with Session(engine, expire_on_commit=False) as session:
        link = session.scalar(select(UserSubscription).where(UserSubscription.subscription_id == 9))
        subscription = session.get(Subscription, 9)
    assert link.is_deleted is True
    assert link.intent_version == 1
    assert subscription.is_deleted is True


def test_new_subscribe_intent_is_not_deduped_by_stale_import_task():
    engine = create_engine('sqlite:///:memory:')
    Base.metadata.create_all(
        engine,
        tables=[
            User.__table__,
            Subscription.__table__,
            UserSubscription.__table__,
            CrawlJob.__table__,
            CrawlTask.__table__,
            CrawlDispatchScope.__table__,
        ],
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
        session.add(User(id=7, nickname='demo'))
        session.add(Subscription(id=9, type='CHANNEL', name='Demo', url='https://www.youtube.com/@demo'))
        session.add(
            UserSubscription(
                user_id=7,
                subscription_id=9,
                is_deleted=False,
                intent_version=0,
            ),
        )

    service = SubscriptionImportService(
        session_factory=session_factory,
        crawl_tasks=CrawlTaskService(session_factory=session_factory),
    )
    service.manage_service.lifecycle = SimpleNamespace(ensure_subscription_syncs=lambda *_args, **_kwargs: None)
    item = SubscriptionImportItem(url='https://www.youtube.com/@demo', name='Demo')
    assert service._enqueue_subscription_tasks([item], user_id=7, site_name='youtube') == 1

    with session_factory() as session:
        link = session.scalar(select(UserSubscription).where(UserSubscription.subscription_id == 9))
        link.is_deleted = True
        link.intent_version = 1
        session.get(Subscription, 9).is_deleted = True

    assert service._enqueue_subscription_tasks([item], user_id=7, site_name='youtube') == 1
    with Session(engine, expire_on_commit=False) as session:
        tasks = session.scalars(
            select(CrawlTask).where(CrawlTask.task_type == 'subscription_import').order_by(CrawlTask.id),
        ).all()
    assert [task.payload['expected_intent_version'] for task in tasks] == [0, 1]
    assert tasks[0].dedupe_key != tasks[1].dedupe_key

    service.process_import_payload(dict(tasks[0].payload))
    service.process_import_payload(dict(tasks[1].payload))

    with Session(engine, expire_on_commit=False) as session:
        link = session.scalar(select(UserSubscription).where(UserSubscription.subscription_id == 9))
        subscription = session.get(Subscription, 9)
    assert link.is_deleted is False
    assert link.intent_version == 2
    assert subscription.is_deleted is False
