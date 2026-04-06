import time

from squirrel_cf_bypass.app.core.cache import ClearanceCache
from squirrel_cf_bypass.app.core.models import ClearanceRecord
from squirrel_cf_bypass.app.core.session_pool import SessionPool


class DummySession:
    def __init__(self):
        self.closed = False

    async def close(self):
        self.closed = True


def test_clearance_cache_expires_entries():
    cache = ClearanceCache(ttl_seconds=0.01)
    record = ClearanceRecord(
        cookies={'cf_clearance': 'demo'},
        user_agent='UA',
        created_at=time.time(),
        expires_at=time.time() + 0.01,
    )
    cache.set('javdb.com', None, record)

    assert cache.get('javdb.com', None) is not None
    time.sleep(0.02)
    assert cache.get('javdb.com', None) is None


def test_session_pool_reuses_and_clears_sessions():
    pool = SessionPool(ttl_seconds=60, max_sessions=8)
    session = DummySession()

    pool.store('javdb.com', None, session)

    assert pool.get('javdb.com', None) is session
    pool.clear_sync()
    assert session.closed is True
