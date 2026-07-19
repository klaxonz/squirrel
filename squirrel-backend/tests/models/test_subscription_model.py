import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from domains.subscription.domain.models.subscription import Subscription, build_subscription_canonical_key
from infrastructure.database.base import Base


def _subscription(*, name: str, url: str | None, canonical_key: str | None = None) -> Subscription:
    values = {
        'type': 'CHANNEL',
        'name': name,
        'url': url,
    }
    if canonical_key is not None:
        values['canonical_key'] = canonical_key
    return Subscription(**values)


def test_canonical_key_tracks_url_on_create_and_assignment():
    subscription = _subscription(name='first', url=' https://example.com/first ')

    assert subscription.canonical_key == build_subscription_canonical_key('https://example.com/first')

    subscription.url = 'https://example.com/second'
    assert subscription.canonical_key == build_subscription_canonical_key('https://example.com/second')

    subscription.url = None
    assert subscription.canonical_key is None


def test_flush_repairs_explicit_stale_canonical_key_and_enforces_url_uniqueness():
    engine = create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine, tables=[Subscription.__table__])

    with Session(engine, expire_on_commit=False) as session:
        first = _subscription(
            name='first',
            url='https://example.com/first',
            canonical_key='stale-explicit-value',
        )
        second = _subscription(name='second', url='https://example.com/second')
        session.add_all([first, second])
        session.commit()

        session.expire(first, ['canonical_key'])
        assert first.canonical_key == build_subscription_canonical_key(first.url)

        first.url = 'https://example.com/renamed'
        session.commit()
        session.expire(first, ['url', 'canonical_key'])
        assert first.canonical_key == build_subscription_canonical_key('https://example.com/renamed')

        second.url = ' https://example.com/renamed '
        assert second.canonical_key == first.canonical_key
        with pytest.raises(IntegrityError):
            session.flush()
