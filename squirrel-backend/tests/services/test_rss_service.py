import json
from datetime import datetime
from unittest.mock import patch

import pytest
import requests
from sqlalchemy import Text, select
from sqlalchemy.orm import Session

from domains.rss.application.services.account.service import RssAccountService
from domains.rss.application.services.client._base import RemoteEntry, RemoteFeed, RssAccountConfig, RssServiceError
from domains.rss.application.services.client._greader import (
    G_READER_QUICK_ENTRIES_PER_FEED,
    G_READER_READING_LIST_STATE,
    GReaderClient,
    _greader_entry_to_remote,
    _greader_normalize_item_id,
)
from domains.rss.application.services.client._miniflux import MinifluxClient
from domains.rss.application.services.credential import decrypt_credential
from domains.rss.application.services.service import RssService
from domains.rss.application.services.sync.service import RssSyncService
from domains.rss.domain.models.rss import RssAccount, RssEntry, RssEntryView, RssFeed
from infrastructure.database.base import Base


@pytest.fixture
def account_svc(session_factory):
    return RssAccountService(session_factory=session_factory)


@pytest.fixture
def sync_svc(session_factory, account_svc):
    return RssSyncService(session_factory=session_factory, account_service=account_svc)


def _create_tables(engine):
    Base.metadata.create_all(
        engine,
        tables=[
            RssAccount.__table__,
            RssFeed.__table__,
            RssEntry.__table__,
            RssEntryView.__table__,
        ],
    )


def test_create_account_encrypts_credential_and_hides_it_from_api(engine, session_factory, account_svc):
    _create_tables(engine)

    account = account_svc.create_account(
        1,
        provider='miniflux',
        name='Reader',
        base_url='https://reader.example/',
        username=None,
        credential='secret-token',
        sync_entry_limit=100,
    )

    assert account['base_url'] == 'https://reader.example'
    assert account['sync_entry_limit'] == 100
    assert account['capabilities'] == {'manage_subscriptions': True}
    assert 'credential' not in account

    with Session(engine) as session:
        row = session.scalars(select(RssAccount)).one()
        assert row.credential_encrypted != 'secret-token'
        assert decrypt_credential(row.credential_encrypted) == 'secret-token'


def test_create_duplicate_account_returns_a_domain_error_instead_of_integrity_error(
    engine, session_factory, account_svc
):
    _create_tables(engine)
    payload = {
        'provider': 'miniflux',
        'name': 'Reader',
        'base_url': 'https://reader.example',
        'username': None,
        'credential': 'secret-token',
    }
    account_svc.create_account(1, **payload)

    with pytest.raises(RssServiceError, match='already exists'):
        account_svc.create_account(1, **payload)

    assert len(account_svc.list_accounts(1)) == 1


def test_sync_account_upserts_feeds_and_entries(engine, session_factory, account_svc, sync_svc):
    _create_tables(engine)
    account = account_svc.create_account(
        1,
        provider='miniflux',
        name='Reader',
        base_url='https://reader.example',
        username=None,
        credential='secret-token',
        sync_entry_limit=100,
    )

    class _FakeClient:
        def list_feeds(self):
            return [
                RemoteFeed(
                    external_feed_id='feed-1',
                    title='Feed One',
                    feed_url='https://example.com/feed.xml',
                    site_url='https://example.com',
                    category='Tech',
                ),
            ]

        def list_entries(self, external_feed_id, limit):
            return [
                RemoteEntry(
                    external_entry_id='entry-1',
                    canonical_url='https://example.com/posts/1',
                    title='Entry One',
                    summary='Body',
                    published_at=datetime(2024, 1, 1, 10, 0, 0),
                ),
            ]

    with patch('domains.rss.application.services.sync.service.create_client', lambda config: _FakeClient()):
        result = sync_svc.sync_account(1, account['id'], entry_limit=20)
    entries = account_svc.list_entries(1)

    assert result == {'account_id': account['id'], 'feeds': 1, 'entries': 1, 'error': None}
    assert account_svc.list_feeds(1)[0]['title'] == 'Feed One'
    assert entries['total'] == 1
    assert entries['data'][0]['title'] == 'Entry One'
    assert account_svc.list_entries(1, query='entry one')['total'] == 1
    assert account_svc.list_entries(1, query='body')['total'] == 1
    assert account_svc.list_entries(1, query='missing')['total'] == 0


def test_list_entries_returns_excerpt_without_full_summary(engine, session_factory, account_svc, sync_svc):
    _create_tables(engine)
    account = account_svc.create_account(
        1,
        provider='miniflux',
        name='Reader',
        base_url='https://reader.example',
        username=None,
        credential='secret-token',
    )

    class _FakeClient:
        def list_feeds(self):
            return [
                RemoteFeed(
                    external_feed_id='feed-1',
                    title='Feed One',
                    feed_url='https://example.com/feed.xml',
                    site_url='https://example.com',
                ),
            ]

        def list_entries(self, external_feed_id, limit):
            return [
                RemoteEntry(
                    external_entry_id='entry-1',
                    canonical_url='https://example.com/posts/1',
                    title='Entry One',
                    summary='<p>Hello <strong>world</strong> from a long article body that should be excerpted.</p>',
                    published_at=datetime(2024, 1, 1, 10, 0, 0),
                ),
            ]

    with patch('domains.rss.application.services.sync.service.create_client', lambda config: _FakeClient()):
        sync_svc.sync_account(1, account['id'], entry_limit=20)

    listed = account_svc.list_entries(1)
    row = listed['data'][0]
    assert row['summary'] is None
    assert row['excerpt'] == 'Hello world from a long article body that should be excerpted.'

    detail = account_svc.get_entry(1, row['id'])
    assert detail is not None
    assert detail['summary'] == '<p>Hello <strong>world</strong> from a long article body that should be excerpted.</p>'
    assert detail['excerpt'] == row['excerpt']

    with Session(engine) as session:
        stored = session.get(RssEntry, row['id'])
        assert stored is not None
        assert stored.raw_data is None


def test_bulk_update_entries_read_status_updates_user_entries_only(engine, session_factory, account_svc, sync_svc):
    _create_tables(engine)
    account = account_svc.create_account(
        1,
        provider='miniflux',
        name='Reader',
        base_url='https://reader.example',
        username=None,
        credential='secret-token',
        enabled=False,
        sync_entry_limit=100,
    )
    other_account = account_svc.create_account(
        2,
        provider='miniflux',
        name='Other Reader',
        base_url='https://other.example',
        username=None,
        credential='other-token',
        enabled=False,
        sync_entry_limit=100,
    )

    with Session(engine) as session:
        feed = RssFeed(
            user_id=1,
            account_id=account['id'],
            external_feed_id='feed-1',
            title='Feed One',
            enabled=True,
        )
        other_feed = RssFeed(
            user_id=2,
            account_id=other_account['id'],
            external_feed_id='feed-2',
            title='Feed Two',
            enabled=True,
        )
        session.add_all([feed, other_feed])
        session.flush()
        entry_one = RssEntry(
            user_id=1,
            account_id=account['id'],
            feed_id=feed.id,
            external_entry_id='entry-1',
            canonical_url='https://example.com/posts/1',
            title='Entry One',
            is_read=False,
            is_starred=False,
        )
        entry_two = RssEntry(
            user_id=1,
            account_id=account['id'],
            feed_id=feed.id,
            external_entry_id='entry-2',
            canonical_url='https://example.com/posts/2',
            title='Entry Two',
            is_read=False,
            is_starred=False,
        )
        other_entry = RssEntry(
            user_id=2,
            account_id=other_account['id'],
            feed_id=other_feed.id,
            external_entry_id='entry-3',
            canonical_url='https://other.example.com/posts/3',
            title='Entry Three',
            is_read=False,
            is_starred=False,
        )
        session.add_all([entry_one, entry_two, other_entry])
        session.commit()
        entry_ids = [entry_one.id, entry_two.id, other_entry.id]

    result = account_svc.update_entries_read_status(1, entry_ids, is_read=True)

    assert result == {'updated': 2}
    with Session(engine) as session:
        rows = session.scalars(select(RssEntry).order_by(RssEntry.id)).all()
        assert [row.is_read for row in rows] == [True, True, False]


def test_record_entry_view_rejects_cross_user_entry_and_recent_list_filters_forged_view(
    engine, session_factory, account_svc
):
    _create_tables(engine)
    own_account = account_svc.create_account(
        1,
        provider='miniflux',
        name='Own Reader',
        base_url='https://own-reader.example',
        username=None,
        credential='own-token',
    )
    other_account = account_svc.create_account(
        2,
        provider='miniflux',
        name='Other Reader',
        base_url='https://other-reader.example',
        username=None,
        credential='other-token',
    )

    with Session(engine) as session:
        own_feed = RssFeed(
            user_id=1,
            account_id=own_account['id'],
            external_feed_id='own-feed',
            title='Own Feed',
            enabled=True,
        )
        other_feed = RssFeed(
            user_id=2,
            account_id=other_account['id'],
            external_feed_id='other-feed',
            title='Other Feed',
            enabled=True,
        )
        session.add_all([own_feed, other_feed])
        session.flush()
        own_entry = RssEntry(
            user_id=1,
            account_id=own_account['id'],
            feed_id=own_feed.id,
            external_entry_id='own-entry',
            canonical_url='https://own.example/posts/1',
            title='Own Entry',
            is_read=False,
            is_starred=False,
        )
        other_entry = RssEntry(
            user_id=2,
            account_id=other_account['id'],
            feed_id=other_feed.id,
            external_entry_id='other-entry',
            canonical_url='https://other.example/posts/1',
            title='Other Entry',
            is_read=False,
            is_starred=False,
        )
        session.add_all([own_entry, other_entry])
        session.commit()
        own_entry_id = own_entry.id
        other_entry_id = other_entry.id

    assert account_svc.record_entry_view(1, other_entry_id) is False
    with Session(engine) as session:
        cross_user_view = session.scalars(
            select(RssEntryView).where(
                RssEntryView.user_id == 1,
                RssEntryView.entry_id == other_entry_id,
            )
        ).first()
        assert cross_user_view is None

        # Simulate a legacy or externally forged row; reads must still enforce ownership.
        session.add(RssEntryView(user_id=1, entry_id=other_entry_id, viewed_at=datetime.now()))
        session.commit()

    assert account_svc.record_entry_view(1, own_entry_id) is True
    recently_viewed = account_svc.list_recently_viewed(1)

    assert [entry['id'] for entry in recently_viewed] == [own_entry_id]
    assert recently_viewed[0]['title'] == 'Own Entry'


def test_delete_account_removes_owned_graph_preserves_other_user_and_allows_recreate(
    engine, session_factory, account_svc
):
    _create_tables(engine)
    account_config = {
        'provider': 'miniflux',
        'name': 'Reader',
        'base_url': 'https://reader.example',
        'username': None,
        'credential': 'secret-token',
    }
    account = account_svc.create_account(1, **account_config)
    other_account = account_svc.create_account(2, **account_config)

    with Session(engine) as session:
        feed = RssFeed(
            user_id=1,
            account_id=account['id'],
            external_feed_id='feed-1',
            title='Feed One',
            enabled=True,
        )
        other_feed = RssFeed(
            user_id=2,
            account_id=other_account['id'],
            external_feed_id='feed-2',
            title='Feed Two',
            enabled=True,
        )
        session.add_all([feed, other_feed])
        session.flush()
        entry = RssEntry(
            user_id=1,
            account_id=account['id'],
            feed_id=feed.id,
            external_entry_id='entry-1',
            canonical_url='https://example.com/posts/1',
            title='Entry One',
            is_read=False,
            is_starred=False,
        )
        other_entry = RssEntry(
            user_id=2,
            account_id=other_account['id'],
            feed_id=other_feed.id,
            external_entry_id='entry-2',
            canonical_url='https://other.example.com/posts/2',
            title='Entry Two',
            is_read=False,
            is_starred=False,
        )
        session.add_all([entry, other_entry])
        session.flush()
        session.add_all(
            [
                RssEntryView(user_id=1, entry_id=entry.id, viewed_at=datetime.now()),
                RssEntryView(user_id=2, entry_id=other_entry.id, viewed_at=datetime.now()),
            ]
        )
        session.commit()
        feed_id = feed.id
        entry_id = entry.id
        other_feed_id = other_feed.id
        other_entry_id = other_entry.id

    assert account_svc.delete_account(1, account['id']) is True

    with Session(engine) as session:
        assert session.get(RssAccount, account['id']) is None
        assert session.get(RssFeed, feed_id) is None
        assert session.get(RssEntry, entry_id) is None
        assert session.scalars(select(RssEntryView).where(RssEntryView.entry_id == entry_id)).first() is None

        assert session.get(RssAccount, other_account['id']) is not None
        assert session.get(RssFeed, other_feed_id) is not None
        assert session.get(RssEntry, other_entry_id) is not None
        assert session.scalars(select(RssEntryView).where(RssEntryView.entry_id == other_entry_id)).one().user_id == 2

    recreated = account_svc.create_account(1, **account_config)
    assert recreated['name'] == account_config['name']
    assert recreated['base_url'] == account_config['base_url']


def test_delete_account_is_rejected_while_sync_holds_the_account_lock(engine, session_factory, account_svc):
    _create_tables(engine)
    account = account_svc.create_account(
        1,
        provider='miniflux',
        name='Reader',
        base_url='https://reader.example',
        username=None,
        credential='secret-token',
    )
    sync_lock = account_svc.sync_lock_for_account(account['id'])
    assert sync_lock.acquire(blocking=False)
    try:
        with pytest.raises(RssServiceError, match='while it is syncing'):
            account_svc.delete_account(1, account['id'])
    finally:
        sync_lock.release()

    assert account_svc.list_accounts(1)[0]['id'] == account['id']


def test_account_mutation_fence_covers_connection_feed_and_view_writes(
    engine,
    session_factory,
    account_svc,
    sync_svc,
):
    _create_tables(engine)
    account = account_svc.create_account(
        1,
        provider='miniflux',
        name='Reader',
        base_url='https://reader.example',
        username=None,
        credential='secret-token',
    )
    with Session(engine) as session:
        feed = RssFeed(
            user_id=1,
            account_id=account['id'],
            external_feed_id='feed-1',
            title='Feed One',
            enabled=True,
        )
        session.add(feed)
        session.flush()
        entry = RssEntry(
            user_id=1,
            account_id=account['id'],
            feed_id=feed.id,
            external_entry_id='entry-1',
            canonical_url='https://example.com/posts/1',
            title='Entry One',
            is_read=False,
            is_starred=False,
        )
        session.add(entry)
        session.commit()
        feed_id = feed.id
        entry_id = entry.id

    mutation_lock = account_svc.mutation_lock_for_account(account['id'])
    assert mutation_lock is account_svc.sync_lock_for_account(account['id'])
    assert mutation_lock.acquire(blocking=False)
    try:
        guarded_calls = (
            lambda: account_svc.update_account(1, account['id'], base_url='https://changed.example'),
            lambda: sync_svc.subscribe_feed(1, account['id'], 'https://example.com/new.xml'),
            lambda: sync_svc.sync_feed(1, feed_id),
            lambda: sync_svc.unsubscribe_feed(1, account['id'], feed_id),
            lambda: account_svc.record_entry_view(1, entry_id),
        )
        for guarded_call in guarded_calls:
            with pytest.raises(RssServiceError, match='syncing or being modified'):
                guarded_call()
    finally:
        mutation_lock.release()

    with Session(engine) as session:
        stored_account = session.get(RssAccount, account['id'])
        assert stored_account.base_url == 'https://reader.example'
        assert session.get(RssFeed, feed_id) is not None
        assert session.scalar(select(RssEntryView.id).where(RssEntryView.entry_id == entry_id)) is None


@pytest.mark.parametrize('provider', ['miniflux', 'fever'])
def test_non_greader_account_defaults_sync_limit_and_name_only_update_preserves_custom_limit(
    provider, engine, session_factory, account_svc
):
    _create_tables(engine)
    account = account_svc.create_account(
        1,
        provider=provider,
        name='Reader',
        base_url='https://reader.example',
        username=None,
        credential='secret-token',
    )
    assert account['sync_entry_limit'] == 100

    customized = account_svc.update_account(1, account['id'], sync_entry_limit=321)
    assert customized['sync_entry_limit'] == 321

    with patch('domains.rss.application.services.service.update_account', account_svc.update_account):
        renamed = RssService().update_account(1, account['id'], name='Renamed Reader')

    assert renamed['name'] == 'Renamed Reader'
    assert renamed['sync_entry_limit'] == 321


def test_fever_account_reports_subscription_management_as_unsupported(engine, session_factory, account_svc):
    _create_tables(engine)
    account = account_svc.create_account(
        1,
        provider='fever',
        name='Fever Reader',
        base_url='https://reader.example',
        username='alice',
        credential='secret-token',
    )

    assert account['capabilities'] == {'manage_subscriptions': False}


def test_rss_entry_title_uses_text_column():
    assert isinstance(RssEntry.__table__.c.title.type, Text)


def test_rss_ownership_graph_declares_cascading_foreign_keys():
    expected_targets = {
        RssFeed.__table__.c.account_id: 'rss_account.id',
        RssEntry.__table__.c.account_id: 'rss_account.id',
        RssEntry.__table__.c.feed_id: 'rss_feed.id',
        RssEntryView.__table__.c.entry_id: 'rss_entry.id',
    }

    for column, expected_target in expected_targets.items():
        foreign_key = next(iter(column.foreign_keys))
        assert foreign_key.target_fullname == expected_target
        assert foreign_key.ondelete == 'CASCADE'


def test_update_entry_submits_remote_status_only_after_local_commit(
    engine,
    session_factory,
    account_svc,
):
    _create_tables(engine)
    account = account_svc.create_account(
        1,
        provider='miniflux',
        name='Reader',
        base_url='https://reader.example',
        username=None,
        credential='secret-token',
    )
    with Session(engine) as session:
        feed = RssFeed(
            user_id=1,
            account_id=account['id'],
            external_feed_id='feed-1',
            title='Feed One',
            enabled=True,
        )
        session.add(feed)
        session.flush()
        entry = RssEntry(
            user_id=1,
            account_id=account['id'],
            feed_id=feed.id,
            external_entry_id='entry-1',
            canonical_url='https://example.com/posts/1',
            title='Entry One',
            is_read=False,
            is_starred=False,
        )
        session.add(entry)
        session.commit()
        entry_id = entry.id

    class _RecordingRemoteStatusSyncer:
        def __init__(self):
            self.calls = []

        def update_entry_async(self, *args, **kwargs):
            self.calls.append((args, kwargs))

        def update_entries_read_status_async(self, *args, **kwargs):
            self.calls.append((args, kwargs))

    remote_syncer = _RecordingRemoteStatusSyncer()
    service = RssAccountService(session_factory=session_factory, remote_status_syncer=remote_syncer)

    with (
        patch.object(Session, 'commit', side_effect=RuntimeError('local commit failed')),
        pytest.raises(RuntimeError, match='local commit failed'),
    ):
        service.update_entry(1, entry_id, is_read=True)

    assert remote_syncer.calls == []
    with Session(engine) as session:
        assert session.get(RssEntry, entry_id).is_read is False


def test_miniflux_client_updates_read_status_and_bookmark():
    class _FakeHttpClient:
        def __init__(self):
            self.put_json_calls = []
            self.put_text_calls = []

        def put_json(self, url, data, headers):
            self.put_json_calls.append((url, data, headers))
            return ''

        def put_text(self, url, headers):
            self.put_text_calls.append((url, headers))
            return ''

    http_client = _FakeHttpClient()
    client = MinifluxClient(
        RssAccountConfig(
            provider='miniflux',
            base_url='https://reader.example',
            username=None,
            credential='secret-token',
        ),
        http_client=http_client,
    )

    client.update_entry('42', is_read=True, is_starred=True)

    assert http_client.put_json_calls == [
        (
            'https://reader.example/v1/entries',
            {'entry_ids': [42], 'status': 'read'},
            {
                'Accept': 'application/json',
                'User-Agent': 'Squirrel/1.0',
                'X-Auth-Token': 'secret-token',
                'Content-Type': 'application/json',
            },
        ),
    ]
    assert http_client.put_text_calls == [
        (
            'https://reader.example/v1/entries/42/bookmark',
            {
                'Accept': 'application/json',
                'User-Agent': 'Squirrel/1.0',
                'X-Auth-Token': 'secret-token',
            },
        ),
    ]


def test_greader_reading_list_category_does_not_mark_entry_read():
    entry = _greader_entry_to_remote(
        {
            'id': 'tag:example.com,2024:item',
            'title': 'Unread Entry',
            'alternate': [{'href': 'https://example.com/posts/unread'}],
            'categories': [
                'user/-/state/com.google/reading-list',
                'user/-/label/Tech',
            ],
        }
    )

    assert entry.is_read is False
    assert entry.is_starred is False


def test_greader_client_fetches_unread_item_ids():
    class _FakeHttpClient:
        def __init__(self):
            self.urls = []

        def post_text(self, url, data, headers):
            return 'Auth=reader-token\n'

        def get_json(self, url, headers):
            self.urls.append(url)
            return {'itemRefs': [{'id': '1782612007899357'}, {'id': 'entry-2'}]}

    http_client = _FakeHttpClient()
    client = GReaderClient(
        RssAccountConfig(
            provider='greader',
            base_url='https://reader.example.com/api/greader.php',
            username='alice',
            credential='api-password',
        ),
        http_client=http_client,
    )

    result = client.fetch_unread_item_ids(limit=200000)

    assert result == ['tag:google.com,2005:reader/item/00065546b380d0dd', 'entry-2']
    assert 'stream/items/ids?' in http_client.urls[0]
    assert 'n=5000' in http_client.urls[0]
    assert 's=user%2F-%2Fstate%2Fcom.google%2Freading-list' in http_client.urls[0]
    assert 'xt=user%2F-%2Fstate%2Fcom.google%2Fread' in http_client.urls[0]


def test_greader_client_paginates_unread_item_ids():
    class _FakeHttpClient:
        def __init__(self):
            self.urls = []

        def post_text(self, url, data, headers):
            return 'Auth=reader-token\n'

        def get_json(self, url, headers):
            self.urls.append(url)
            if 'c=' not in url:
                return {
                    'itemRefs': [{'id': '1782612007899357'}],
                    'continuation': '1782612007899357',
                }
            return {'itemRefs': [{'id': 'entry-2'}]}

    http_client = _FakeHttpClient()
    client = GReaderClient(
        RssAccountConfig(
            provider='greader',
            base_url='https://reader.example.com/api/greader.php',
            username='alice',
            credential='api-password',
        ),
        http_client=http_client,
    )

    result = client.fetch_unread_item_ids(limit=200000)

    assert result == ['tag:google.com,2005:reader/item/00065546b380d0dd', 'entry-2']
    assert len(http_client.urls) == 2
    assert 'n=5000' in http_client.urls[0]
    assert 'c=1782612007899357' in http_client.urls[1]


def test_greader_client_reports_unread_item_id_progress():
    class _FakeHttpClient:
        def __init__(self):
            self.urls = []

        def post_text(self, url, data, headers):
            return 'Auth=reader-token\n'

        def get_json(self, url, headers):
            self.urls.append(url)
            if 'c=' not in url:
                return {
                    'itemRefs': [{'id': '1782612007899357'}],
                    'continuation': '1782612007899357',
                }
            return {'itemRefs': [{'id': 'entry-2'}]}

    http_client = _FakeHttpClient()
    client = GReaderClient(
        RssAccountConfig(
            provider='greader',
            base_url='https://reader.example.com/api/greader.php',
            username='alice',
            credential='api-password',
        ),
        http_client=http_client,
    )
    progress = []

    result = client.fetch_unread_item_ids(
        limit=200000,
        progress_callback=lambda count, has_more: progress.append((count, has_more)),
    )

    assert result == ['tag:google.com,2005:reader/item/00065546b380d0dd', 'entry-2']
    assert progress == [(1, True), (2, False)]


def test_json_http_client_retries_transient_timeouts(monkeypatch):
    from domains.rss.application.services.client._base import _JsonHttpClient

    attempts = {'count': 0}

    class _Response:
        def raise_for_status(self):
            return None

        def json(self):
            return {'ok': True}

    class _Session:
        def request(self, method, url, headers=None, data=None, timeout=None):
            attempts['count'] += 1
            if attempts['count'] < 3:
                raise requests.exceptions.ReadTimeout('The read operation timed out')
            return _Response()

    monkeypatch.setattr('domains.rss.application.services.client._base.time.sleep', lambda *_args, **_kwargs: None)

    client = _JsonHttpClient(timeout=1, retries=3, retry_backoff_seconds=0, session=_Session())
    result = client.get_json('https://reader.example.com/ping', {'Accept': 'application/json'})

    assert result == {'ok': True}
    assert attempts['count'] == 3


def test_greader_normalizes_decimal_item_id_to_entry_id():
    assert _greader_normalize_item_id('1782612007899357') == 'tag:google.com,2005:reader/item/00065546b380d0dd'
    assert _greader_normalize_item_id('tag:google.com,2005:reader/item/00065546b380d0dd') == (
        'tag:google.com,2005:reader/item/00065546b380d0dd'
    )


def test_greader_client_fetches_item_contents_with_repeated_item_ids():
    class _FakeHttpClient:
        def __init__(self):
            self.posted = []

        def post_text(self, url, data, headers):
            self.posted.append((url, data, headers))
            if url.endswith('/accounts/ClientLogin'):
                return 'Auth=reader-token\n'
            return json.dumps(
                {
                    'items': [
                        {
                            'id': '1782612007899357',
                            'title': 'Unread Entry',
                            'alternate': [{'href': 'https://example.com/posts/unread'}],
                            'origin': {'streamId': 'feed/1'},
                        }
                    ]
                }
            )

    http_client = _FakeHttpClient()
    client = GReaderClient(
        RssAccountConfig(
            provider='greader',
            base_url='https://reader.example.com/api/greader.php',
            username='alice',
            credential='api-password',
        ),
        http_client=http_client,
    )

    entries = client.fetch_items_contents(['tag:google.com,2005:reader/item/00065546b380d0dd'])

    assert entries[0].external_entry_id == 'tag:google.com,2005:reader/item/00065546b380d0dd'
    assert http_client.posted[-1][1] == [('i', 'tag:google.com,2005:reader/item/00065546b380d0dd')]


def test_greader_client_uses_client_login_and_stream_api():
    class _FakeHttpClient:
        def __init__(self):
            self.posted = []
            self.requested = []

        def post_text(self, url, data, headers):
            self.posted.append((url, data, headers))
            return 'SID=session\nLSID=long-session\nAuth=reader-token\n'

        def get_json(self, url, headers):
            self.requested.append((url, headers))
            if url.endswith('/reader/api/0/subscription/list?output=json'):
                return {
                    'subscriptions': [
                        {
                            'id': 'feed/https://example.com/feed.xml',
                            'title': 'Example Feed',
                            'htmlUrl': 'https://example.com',
                            'categories': [{'label': 'Tech'}],
                        },
                    ],
                }
            return {
                'items': [
                    {
                        'id': 'tag:example.com,2024:item',
                        'title': 'Example Entry',
                        'alternate': [{'href': 'https://example.com/posts/1'}],
                        'summary': {'content': 'Body'},
                        'published': 1704103200,
                        'categories': ['user/-/state/com.google/read'],
                        'enclosures': [{'url': 'https://cdn.example.com/audio.mp3', 'type': 'audio/mpeg'}],
                    },
                ],
            }

    http_client = _FakeHttpClient()
    client = GReaderClient(
        RssAccountConfig(
            provider='greader',
            base_url='https://reader.example.com/api/greader.php',
            username='alice',
            credential='api-password',
        ),
        http_client=http_client,
    )

    feeds = client.list_feeds()
    entries = client.list_entries(feeds[0].external_feed_id, 20)

    assert http_client.posted[0][0] == 'https://reader.example.com/api/greader.php/accounts/ClientLogin'
    assert http_client.posted[0][1] == {'Email': 'alice', 'Passwd': 'api-password'}
    assert http_client.requested[0][1]['Authorization'] == 'GoogleLogin auth=reader-token'
    assert feeds[0].external_feed_id == 'feed/https://example.com/feed.xml'
    assert feeds[0].category == 'Tech'
    assert '/reader/api/0/stream/contents/feed/https%3A//example.com/feed.xml?' in http_client.requested[1][0]
    assert entries[0].title == 'Example Entry'
    assert entries[0].canonical_url == 'https://example.com/posts/1'
    assert entries[0].is_read is True


def test_greader_client_paginates_reading_list():
    class _FakeHttpClient:
        def __init__(self):
            self.urls = []

        def post_text(self, url, data, headers):
            return 'Auth=reader-token\n'

        def get_json(self, url, headers):
            self.urls.append(url)
            if 'c=next-page' in url:
                return {
                    'items': [
                        {
                            'id': 'entry-2',
                            'title': 'Entry Two',
                            'alternate': [{'href': 'https://example.com/posts/2'}],
                            'origin': {'streamId': 'feed/1'},
                        },
                    ],
                }
            return {
                'items': [
                    {
                        'id': 'entry-1',
                        'title': 'Entry One',
                        'alternate': [{'href': 'https://example.com/posts/1'}],
                        'origin': {'streamId': 'feed/1'},
                    },
                ],
                'continuation': 'next-page',
            }

    http_client = _FakeHttpClient()
    client = GReaderClient(
        RssAccountConfig(
            provider='greader',
            base_url='https://reader.example.com/api/greader.php',
            username='alice',
            credential='api-password',
        ),
        http_client=http_client,
    )

    entries = client.list_recent_entries(None)

    assert [entry.title for entry in entries] == ['Entry One', 'Entry Two']
    assert len(http_client.urls) == 2
    assert f'stream/contents/{G_READER_READING_LIST_STATE}?output=json&n=1000' in http_client.urls[0]
    assert 'c=next-page' in http_client.urls[1]


def test_sync_greader_uses_reading_list_entries(engine, session_factory, account_svc, sync_svc):
    _create_tables(engine)
    account = account_svc.create_account(
        1,
        provider='greader',
        name='FreshRSS',
        base_url='https://reader.example.com/api/greader.php',
        username='alice',
        credential='api-password',
    )

    class _FakeGReaderClient(GReaderClient):
        def __init__(self):
            super().__init__(
                RssAccountConfig(
                    provider='greader',
                    base_url='https://reader.example.com/api/greader.php',
                    username='alice',
                    credential='api-password',
                )
            )
            self.per_feed_calls = 0

        def list_feeds(self):
            return [
                RemoteFeed(
                    external_feed_id='feed/5815',
                    title='AI at Meta Blog',
                    feed_url='https://ai.meta.com/blog/rss',
                ),
            ]

        def list_entries(self, external_feed_id, limit):
            self.per_feed_calls += 1
            return []

        def iter_recent_entries(self, limit, progress_callback=None):
            if progress_callback:
                progress_callback(1, None)
            yield [
                RemoteEntry(
                    external_feed_id='feed/5815',
                    external_entry_id='entry-1',
                    canonical_url='https://ai.meta.com/blog/post',
                    title='Entry One',
                    published_at=datetime(2024, 1, 1, 10, 0, 0),
                ),
            ]

        def fetch_all_item_ids(self, stream_id='reading-list', limit=200000, progress_callback=None):
            return ['entry-1']

        def fetch_unread_item_ids(self, limit=200000, progress_callback=None):
            return ['entry-1']

        def fetch_items_contents(self, entry_ids):
            return []

    client = _FakeGReaderClient()
    with patch('domains.rss.application.services.sync.service.create_client', lambda config: client):
        result = sync_svc.sync_account(1, account['id'])
    entries = account_svc.list_entries(1)

    assert result == {'account_id': account['id'], 'feeds': 1, 'entries': 1, 'error': None}
    assert entries['data'][0]['title'] == 'Entry One'


def test_sync_greader_imports_missing_unread_entries(engine, session_factory, account_svc, sync_svc):
    _create_tables(engine)
    account = account_svc.create_account(
        1,
        provider='greader',
        name='FreshRSS',
        base_url='https://reader.example.com/api/greader.php',
        username='alice',
        credential='api-password',
    )

    with Session(engine) as session:
        feed = RssFeed(
            user_id=1,
            account_id=account['id'],
            external_feed_id='feed/1',
            title='Feed One',
            enabled=True,
        )
        session.add(feed)
        session.flush()
        session.add(
            RssEntry(
                user_id=1,
                account_id=account['id'],
                feed_id=feed.id,
                external_entry_id='tag:google.com,2005:reader/item/00065546b380d0dd',
                canonical_url='https://example.com/posts/existing',
                title='Existing Entry',
                is_read=True,
                is_starred=False,
            ),
        )
        session.add(
            RssEntry(
                user_id=1,
                account_id=account['id'],
                feed_id=feed.id,
                external_entry_id='tag:google.com,2005:reader/item/00065546b380d0dc',
                canonical_url='https://example.com/posts/read',
                title='Read Entry',
                is_read=False,
                is_starred=False,
            ),
        )
        session.commit()

    class _FakeGReaderClient(GReaderClient):
        def __init__(self):
            super().__init__(
                RssAccountConfig(
                    provider='greader',
                    base_url='https://reader.example.com/api/greader.php',
                    username='alice',
                    credential='api-password',
                )
            )
            self.content_requests = []

        def list_feeds(self):
            return [
                RemoteFeed(
                    external_feed_id='feed/1',
                    title='Feed One',
                    feed_url='https://example.com/feed.xml',
                ),
            ]

        def iter_recent_entries(self, limit, progress_callback=None):
            if False:
                yield []

        def fetch_unread_item_ids(self, limit=200000, progress_callback=None):
            return [
                'tag:google.com,2005:reader/item/00065546b380d0dd',
                'tag:google.com,2005:reader/item/00065546b380d0de',
            ]

        def fetch_items_contents(self, entry_ids):
            self.content_requests.append(list(entry_ids))
            return [
                RemoteEntry(
                    external_feed_id='feed/1',
                    external_entry_id='tag:google.com,2005:reader/item/00065546b380d0de',
                    canonical_url='https://example.com/posts/missing',
                    title='Missing Entry',
                    is_read=False,
                ),
            ]

        def fetch_all_item_ids(self, stream_id='reading-list', limit=200000, progress_callback=None):
            raise AssertionError('incremental sync should not run full state reconciliation')

    client = _FakeGReaderClient()
    with patch('domains.rss.application.services.sync.service.create_client', lambda config: client):
        sync_svc.sync_account(1, account['id'])

    unread = account_svc.list_entries(1, account_id=account['id'], is_read=False)
    with Session(engine) as session:
        read_entry = session.scalars(
            select(RssEntry).where(
                RssEntry.account_id == account['id'],
                RssEntry.external_entry_id == 'tag:google.com,2005:reader/item/00065546b380d0dc',
            )
        ).one()

    assert unread['total'] == 2
    assert [entry['external_entry_id'] for entry in unread['data']] == [
        'tag:google.com,2005:reader/item/00065546b380d0de',
        'tag:google.com,2005:reader/item/00065546b380d0dd',
    ]
    assert read_entry.is_read is True
    assert client.content_requests == [['tag:google.com,2005:reader/item/00065546b380d0de']]


def test_sync_progress_reports_completed_state(engine, session_factory, account_svc, sync_svc):
    _create_tables(engine)
    account = account_svc.create_account(
        1,
        provider='greader',
        name='FreshRSS',
        base_url='https://reader.example.com/api/greader.php',
        username='alice',
        credential='api-password',
    )

    class _FakeGReaderClient(GReaderClient):
        def __init__(self):
            super().__init__(
                RssAccountConfig(
                    provider='greader',
                    base_url='https://reader.example.com/api/greader.php',
                    username='alice',
                    credential='api-password',
                )
            )

        def list_feeds(self):
            return [
                RemoteFeed(
                    external_feed_id='feed/1',
                    title='Feed One',
                    feed_url='https://example.com/feed.xml',
                ),
            ]

        def iter_recent_entries(self, limit, progress_callback=None):
            if progress_callback:
                progress_callback(1, None)
            yield [
                RemoteEntry(
                    external_feed_id='feed/1',
                    external_entry_id='entry-1',
                    canonical_url='https://example.com/posts/1',
                    title='Entry One',
                ),
            ]

        def fetch_all_item_ids(self, stream_id='reading-list', limit=200000, progress_callback=None):
            return ['entry-1']

        def fetch_unread_item_ids(self, limit=200000, progress_callback=None):
            return ['entry-1']

        def fetch_items_contents(self, entry_ids):
            return []

    with patch('domains.rss.application.services.sync.service.create_client', lambda config: _FakeGReaderClient()):
        sync_svc.sync_account(1, account['id'])
    progress = account_svc.get_sync_progress(1, account['id'])

    assert progress['running'] is False
    assert progress['phase'] == 'completed'
    assert progress['feeds_synced'] == 1
    assert progress['entries_synced'] == 1


def test_greader_incremental_sync_stops_when_page_has_no_changes(engine, session_factory, account_svc, sync_svc):
    _create_tables(engine)
    account = account_svc.create_account(
        1,
        provider='greader',
        name='FreshRSS',
        base_url='https://reader.example.com/api/greader.php',
        username='alice',
        credential='api-password',
    )

    with Session(engine) as session:
        feed = RssFeed(
            user_id=1,
            account_id=account['id'],
            external_feed_id='feed/1',
            title='Feed One',
            enabled=True,
        )
        session.add(feed)
        session.flush()
        session.add(
            RssEntry(
                user_id=1,
                account_id=account['id'],
                feed_id=feed.id,
                external_entry_id='entry-1',
                canonical_url='https://example.com/posts/1',
                title='Entry One',
                published_at=datetime(2024, 1, 1, 10, 0, 0),
                is_read=False,
                is_starred=False,
            ),
        )
        session.commit()

    class _FakeGReaderClient(GReaderClient):
        def __init__(self):
            super().__init__(
                RssAccountConfig(
                    provider='greader',
                    base_url='https://reader.example.com/api/greader.php',
                    username='alice',
                    credential='api-password',
                )
            )
            self.pages_requested = 0
            self.entry_limit = None

        def list_feeds(self):
            return [
                RemoteFeed(
                    external_feed_id='feed/1',
                    title='Feed One',
                    feed_url='https://example.com/feed.xml',
                ),
            ]

        def iter_recent_entries(self, limit, progress_callback=None):
            self.pages_requested += 1
            self.entry_limit = limit
            if progress_callback:
                progress_callback(1, 'next-page')
            yield [
                RemoteEntry(
                    external_feed_id='feed/1',
                    external_entry_id='entry-1',
                    canonical_url='https://example.com/posts/1',
                    title='Entry One',
                    published_at=datetime(2024, 1, 1, 10, 0, 0),
                ),
            ]
            raise AssertionError('incremental sync should stop before requesting older pages')

        def fetch_all_item_ids(self, stream_id='reading-list', limit=200000, progress_callback=None):
            raise AssertionError('incremental sync should not run full state reconciliation')

        def fetch_unread_item_ids(self, limit=200000, progress_callback=None):
            return ['entry-1']

        def fetch_items_contents(self, entry_ids):
            return []

    client = _FakeGReaderClient()
    with patch('domains.rss.application.services.sync.service.create_client', lambda config: client):
        result = sync_svc.sync_account(1, account['id'])
    progress = account_svc.get_sync_progress(1, account['id'])

    assert result == {'account_id': account['id'], 'feeds': 1, 'entries': 0, 'error': None}
    assert client.pages_requested == 1
    assert client.entry_limit == G_READER_QUICK_ENTRIES_PER_FEED
    assert progress['sync_mode'] == 'incremental'


def test_greader_full_sync_reconciles_read_and_starred_state(engine, session_factory, account_svc, sync_svc):
    _create_tables(engine)
    account = account_svc.create_account(
        1,
        provider='greader',
        name='FreshRSS',
        base_url='https://reader.example.com/api/greader.php',
        username='alice',
        credential='api-password',
    )
    other_account = account_svc.create_account(
        1,
        provider='greader',
        name='Other FreshRSS',
        base_url='https://reader.example.com/api/greader.php',
        username='alice',
        credential='api-password',
    )

    with Session(engine) as session:
        feed = RssFeed(
            user_id=1,
            account_id=account['id'],
            external_feed_id='feed/1',
            title='Feed One',
            enabled=True,
        )
        session.add(feed)
        session.flush()
        session.add(
            RssEntry(
                user_id=1,
                account_id=account['id'],
                feed_id=feed.id,
                external_entry_id='entry-1',
                canonical_url='https://example.com/posts/1',
                title='Entry One',
                is_read=False,
                is_starred=False,
            ),
        )
        removed_entry = RssEntry(
            user_id=1,
            account_id=account['id'],
            feed_id=feed.id,
            external_entry_id='entry-removed',
            canonical_url='https://example.com/posts/removed',
            title='Removed Entry',
            is_read=False,
            is_starred=False,
        )
        session.add(removed_entry)
        session.flush()
        removed_entry_view = RssEntryView(user_id=1, entry_id=removed_entry.id, viewed_at=datetime.now())
        session.add(removed_entry_view)
        other_feed = RssFeed(
            user_id=1,
            account_id=other_account['id'],
            external_feed_id='feed/other',
            title='Other Feed',
            enabled=True,
        )
        session.add(other_feed)
        session.flush()
        session.add(
            RssEntry(
                user_id=1,
                account_id=other_account['id'],
                feed_id=other_feed.id,
                external_entry_id='entry-removed',
                canonical_url='https://other.example.com/posts/removed',
                title='Other Removed Entry',
                is_read=False,
                is_starred=False,
            ),
        )
        session.commit()
        removed_entry_id = removed_entry.id
        removed_entry_view_id = removed_entry_view.id

    class _FakeGReaderClient(GReaderClient):
        def __init__(self):
            super().__init__(
                RssAccountConfig(
                    provider='greader',
                    base_url='https://reader.example.com/api/greader.php',
                    username='alice',
                    credential='api-password',
                )
            )
            self.state_streams = []

        def list_feeds(self):
            return [
                RemoteFeed(
                    external_feed_id='feed/1',
                    title='Feed One',
                    feed_url='https://example.com/feed.xml',
                ),
            ]

        def iter_recent_entries(self, limit, progress_callback=None):
            if False:
                yield []

        def fetch_all_item_ids(self, stream_id='reading-list', limit=200000, progress_callback=None):
            self.state_streams.append(stream_id)
            if stream_id == G_READER_READING_LIST_STATE:
                return ['entry-1']
            if stream_id == 'user/-/state/com.google/read':
                return ['entry-1']
            if stream_id == 'user/-/state/com.google/starred':
                return ['entry-1']
            return []

        def fetch_unread_item_ids(self, limit=200000, progress_callback=None):
            return []

        def fetch_items_contents(self, entry_ids):
            return []

    client = _FakeGReaderClient()
    with patch('domains.rss.application.services.sync.service.create_client', lambda config: client):
        sync_svc.sync_account(1, account['id'], force_full_sync=True)

    with Session(engine) as session:
        entry = session.scalars(
            select(RssEntry).where(
                RssEntry.account_id == account['id'],
                RssEntry.external_entry_id == 'entry-1',
            )
        ).one()
        other_entry = session.scalars(
            select(RssEntry).where(
                RssEntry.account_id == other_account['id'],
                RssEntry.external_entry_id == 'entry-removed',
            )
        ).one()
        assert entry.is_read is True
        assert entry.is_starred is True
        assert other_entry.title == 'Other Removed Entry'
        assert session.get(RssEntry, removed_entry_id) is None
        assert session.get(RssEntryView, removed_entry_view_id) is None
    assert client.state_streams == [
        G_READER_READING_LIST_STATE,
        'user/-/state/com.google/read',
        'user/-/state/com.google/starred',
    ]
