from contextlib import contextmanager
from contextvars import ContextVar

from infrastructure.database import session as database

_session_factory: ContextVar = ContextVar('subscription_sync_session_factory', default=None)


def get_session():
    factory = _session_factory.get()
    return (factory or database.get_session)()


@contextmanager
def use_session_factory(factory):
    token = _session_factory.set(factory)
    try:
        yield
    finally:
        _session_factory.reset(token)
