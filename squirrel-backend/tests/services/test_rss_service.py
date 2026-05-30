from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
import sys

from sqlalchemy import Text, create_engine, select
from sqlalchemy.orm import Session

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from models import Base
from models.rss import RssAccount, RssEntry, RssFeed
from services import rss_service


@contextmanager
def _managed_session(engine):
    session = Session(engine, expire_on_commit=False)
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def _setup(monkeypatch):
    engine = create_engine('sqlite:///:memory:')
    Base.metadata.create_all(
        engine,
        tables=[
            RssAccount.__table__,
            RssFeed.__table__,
            RssEntry.__table__,
        ],
    )
    monkeypatch.setattr(rss_service, 'get_session', lambda: _managed_session(engine))
    return engine


def test_create_account_encrypts_credential_and_hides_it_from_api(monkeypatch):
    engine = _setup(monkeypatch)

    account = rss_service.create_account(
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
    assert 'credential' not in account

    with Session(engine) as session:
        row = session.scalars(select(RssAccount)).one()
        assert row.credential_encrypted != 'secret-token'
        assert rss_service._decrypt(row.credential_encrypted) == 'secret-token'


def test_sync_account_upserts_feeds_and_entries(monkeypatch):
    _setup(monkeypatch)
    account = rss_service.create_account(
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
                rss_service.RemoteFeed(
                    external_feed_id='feed-1',
                    title='Feed One',
                    feed_url='https://example.com/feed.xml',
                    site_url='https://example.com',
                    category='Tech',
                )
            ]

        def list_entries(self, external_feed_id, limit):
            return [
                rss_service.RemoteEntry(
                    external_entry_id='entry-1',
                    canonical_url='https://example.com/posts/1',
                    title='Entry One',
                    summary='Body',
                    published_at=datetime(2024, 1, 1, 10, 0, 0),
                )
            ]

    monkeypatch.setattr(rss_service, '_client_for_config', lambda config: _FakeClient())

    result = rss_service.sync_account(1, account['id'], entry_limit=20)
    entries = rss_service.list_entries(1)

    assert result == {'account_id': account['id'], 'feeds': 1, 'entries': 1, 'error': None}
    assert rss_service.list_feeds(1)[0]['title'] == 'Feed One'
    assert entries['total'] == 1
    assert entries['data'][0]['title'] == 'Entry One'


def test_rss_entry_title_uses_text_column():
    assert isinstance(RssEntry.__table__.c.title.type, Text)


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
                        }
                    ]
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
                    }
                ]
            }

    http_client = _FakeHttpClient()
    client = rss_service.GReaderClient(
        rss_service.RssAccountConfig(
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
                        }
                    ]
                }
            return {
                'items': [
                    {
                        'id': 'entry-1',
                        'title': 'Entry One',
                        'alternate': [{'href': 'https://example.com/posts/1'}],
                        'origin': {'streamId': 'feed/1'},
                    }
                ],
                'continuation': 'next-page',
            }

    http_client = _FakeHttpClient()
    client = rss_service.GReaderClient(
        rss_service.RssAccountConfig(
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
    assert 'stream/contents/reading-list?output=json&n=1000' in http_client.urls[0]
    assert 'c=next-page' in http_client.urls[1]


def test_sync_greader_uses_reading_list_entries(monkeypatch):
    _setup(monkeypatch)
    account = rss_service.create_account(
        1,
        provider='greader',
        name='FreshRSS',
        base_url='https://reader.example.com/api/greader.php',
        username='alice',
        credential='api-password',
    )

    class _FakeGReaderClient(rss_service.GReaderClient):
        def __init__(self):
            super().__init__(rss_service.RssAccountConfig(
                provider='greader',
                base_url='https://reader.example.com/api/greader.php',
                username='alice',
                credential='api-password',
            ))
            self.per_feed_calls = 0

        def list_feeds(self):
            return [
                rss_service.RemoteFeed(
                    external_feed_id='feed/5815',
                    title='AI at Meta Blog',
                    feed_url='https://ai.meta.com/blog/rss',
                )
            ]

        def list_entries(self, external_feed_id, limit):
            self.per_feed_calls += 1
            return []

        def iter_recent_entries(self, limit, progress_callback=None):
            if progress_callback:
                progress_callback(1, None)
            yield [
                rss_service.RemoteEntry(
                    external_feed_id='feed/5815',
                    external_entry_id='entry-1',
                    canonical_url='https://ai.meta.com/blog/post',
                    title='Entry One',
                    published_at=datetime(2024, 1, 1, 10, 0, 0),
                )
            ]

        def fetch_all_item_ids(self, stream_id='reading-list', limit=200000):
            return ['entry-1']

    client = _FakeGReaderClient()
    monkeypatch.setattr(rss_service, '_client_for_config', lambda config: client)

    result = rss_service.sync_account(1, account['id'])
    entries = rss_service.list_entries(1)

    assert result == {'account_id': account['id'], 'feeds': 1, 'entries': 1, 'error': None}
    assert entries['data'][0]['title'] == 'Entry One'


def test_sync_progress_reports_completed_state(monkeypatch):
    _setup(monkeypatch)
    account = rss_service.create_account(
        1,
        provider='greader',
        name='FreshRSS',
        base_url='https://reader.example.com/api/greader.php',
        username='alice',
        credential='api-password',
    )

    class _FakeGReaderClient(rss_service.GReaderClient):
        def __init__(self):
            super().__init__(rss_service.RssAccountConfig(
                provider='greader',
                base_url='https://reader.example.com/api/greader.php',
                username='alice',
                credential='api-password',
            ))

        def list_feeds(self):
            return [
                rss_service.RemoteFeed(
                    external_feed_id='feed/1',
                    title='Feed One',
                    feed_url='https://example.com/feed.xml',
                )
            ]

        def iter_recent_entries(self, limit, progress_callback=None):
            if progress_callback:
                progress_callback(1, None)
            yield [
                rss_service.RemoteEntry(
                    external_feed_id='feed/1',
                    external_entry_id='entry-1',
                    canonical_url='https://example.com/posts/1',
                    title='Entry One',
                )
            ]

        def fetch_all_item_ids(self, stream_id='reading-list', limit=200000):
            return ['entry-1']

    monkeypatch.setattr(rss_service, '_client_for_config', lambda config: _FakeGReaderClient())

    rss_service.sync_account(1, account['id'])
    progress = rss_service.get_sync_progress(1, account['id'])

    assert progress['running'] is False
    assert progress['phase'] == 'completed'
    assert progress['feeds_synced'] == 1
    assert progress['entries_synced'] == 1
