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
    e = create_engine('sqlite:///:memory:')
    return e


@pytest.fixture
def session_factory(engine):
    return lambda: _get_session(engine)


@pytest.fixture
def suppress_postgres(monkeypatch):
    from infrastructure.database import session as database

    monkeypatch.setattr(database, 'register_after_commit', lambda session, callback: None)


@pytest.fixture
def sss_session(session_factory):
    from domains.subscription.application.services.core.sync.state.service import SubscriptionSyncStateService

    return SubscriptionSyncStateService(session_factory=session_factory)
