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
def sss_session(monkeypatch, session_factory):
    """Redirect subscription_sync_state_service's module-level get_session to our session_factory."""
    from core import database
    monkeypatch.setattr(database, "get_session", session_factory)

    from services.subscription_sync_run_service import _default as run_svc_default
    run_svc_default.next_seq_no = lambda stream_id, *, session=None: 1

    from services.subscription_sync_projection_service import _default as proj_default
    proj_default._advisory_lock = staticmethod(lambda session, key: None)
    proj_default.apply_event = lambda event, session=None: event

