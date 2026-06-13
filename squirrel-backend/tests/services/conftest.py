from contextlib import contextmanager

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session


@contextmanager
def _get_session(engine):
    session = Session(engine, expire_on_commit=False)
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


@pytest.fixture
def engine():
    e = create_engine("sqlite:///:memory:")
    return e


@pytest.fixture
def session_factory(engine):
    return lambda: _get_session(engine)


@pytest.fixture
def suppress_postgres(monkeypatch):
    from core import database
    monkeypatch.setattr(database, "register_after_commit", lambda session, callback: None)


@pytest.fixture
def sss_session(session_factory):
    """Redirect module-level services to use test session_factory via direct attribute assignment."""
    from core import database
    database.get_session = session_factory

    from domains.subscription.application.services.crawl.tasks import service as crawl_task_service_mod
    crawl_task_service_mod.crawl_task_service.session_factory = session_factory

    from domains.subscription.application.services.core.sync.run_service import subscription_sync_run_service
    _seq_counters: dict[str, int] = {}
    def _next_seq_no(stream_id, *, session=None):
        _seq_counters[stream_id] = _seq_counters.get(stream_id, 0) + 1
        return _seq_counters[stream_id]
    subscription_sync_run_service.next_seq_no = _next_seq_no

    import subscription.services.core.sync.projection.store as projection_store
    from domains.subscription.application.services.core.sync.projection.service import subscription_sync_projection_service
    projection_store.advisory_lock = lambda session, key: None
    subscription_sync_projection_service.apply_event = lambda event, session=None: event

    from domains.subscription.application.services.sync.stream_service import sync_dashboard_stream_service
    sync_dashboard_stream_service.publish_sync_dashboard_invalidation = staticmethod(lambda channel, payload=None: None)
