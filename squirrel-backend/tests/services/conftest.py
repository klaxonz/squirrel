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

    from services.crawl_tasks import service as crawl_task_service_mod
    crawl_task_service_mod._default.session_factory = session_factory

    from services.subscription_sync_run_service import _default as run_svc_default
    _seq_counters: dict[str, int] = {}
    def _next_seq_no(stream_id, *, session=None):
        _seq_counters[stream_id] = _seq_counters.get(stream_id, 0) + 1
        return _seq_counters[stream_id]
    run_svc_default.next_seq_no = _next_seq_no

    from services.subscription_sync_projection_service import _default as proj_default
    proj_default._advisory_lock = staticmethod(lambda session, key: None)
    proj_default.apply_event = lambda event, session=None: event

    # Make stream_service constants available on the default instance
    from services.sync_center_stream_service import (
        SYNC_CENTER_FEED_CHANNEL,
        SYNC_CENTER_RUN_CHANNEL,
    )
    from services.sync_center_stream_service import _default as stream_default
    stream_default.SYNC_CENTER_FEED_CHANNEL = SYNC_CENTER_FEED_CHANNEL
    stream_default.SYNC_CENTER_RUN_CHANNEL = SYNC_CENTER_RUN_CHANNEL
    stream_default.publish_sync_center_invalidation = staticmethod(lambda channel, payload=None: None)

