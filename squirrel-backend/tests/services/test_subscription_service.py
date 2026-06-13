from datetime import datetime
from types import SimpleNamespace

import pytest
from sqlalchemy.orm import Session

from shared_kernel.domain.base import Base
from domains.video.domain.junctions.subscription_video import SubscriptionVideo, UserSubscription
from domains.subscription.domain.models.subscription import Subscription
from domains.subscription.domain.models.subscription_sync_state import SubscriptionSyncState
from domains.subscription.application.services.core.crud import SubscriptionCrudService
from domains.subscription.application.services.core.import_service import SubscriptionImportService
from domains.subscription.application.services.core.listing.service import SubscriptionListService
from domains.subscription.application.services.core.manage import SubscriptionManageService
from domains.user.domain.models.user import User
from domains.user.domain.models.user_video_feed import UserVideoFeed
from domains.video.domain.models.video import Video
from domains.video.domain.models.video_history import VideoHistory


def _get_user_config(_user_id):
    return {"showNsfw": True}


@pytest.fixture(autouse=True)
def _redirect_module_services(session_factory):
    """Redirect module-level service instances to use test session_factory."""
    from core import database
    database.get_session = session_factory

    from domains.subscription.application.services.crawl.tasks import service as crawl_task_service_mod
    crawl_task_service_mod.crawl_task_service.session_factory = session_factory

    import user.services.feed as uvfs
    uvfs.user_video_feed_service._session_factory = session_factory

    from domains.video.application.services.extraction_projection.service import video_extraction_projection_service
    video_extraction_projection_service.session_factory = session_factory

    from domains.subscription.application.services.core.crud import subscription_crud_service
    subscription_crud_service.session_factory = session_factory

    from domains.subscription.application.services.core.manage import subscription_manage_service
    subscription_manage_service.session_factory = session_factory


@pytest.fixture
def engine(engine):
    Base.metadata.create_all(
        engine,
        tables=[
            Subscription.__table__,
            Video.__table__,
            SubscriptionVideo.__table__,
            User.__table__,
            UserSubscription.__table__,
            UserVideoFeed.__table__,
            SubscriptionSyncState.__table__,
            VideoHistory.__table__,
        ],
    )
    return engine


@pytest.fixture
def crud(session_factory):
    return SubscriptionCrudService(session_factory=session_factory)


@pytest.fixture
def manage(session_factory):
    return SubscriptionManageService(session_factory=session_factory)


@pytest.fixture
def import_svc(session_factory):
    return SubscriptionImportService(session_factory=session_factory)


@pytest.fixture
def list_svc(session_factory):
    return SubscriptionListService(session_factory=session_factory, get_user_config=_get_user_config)


def _seed_subscription(engine, *, subscription_id: int = 1, user_ids: list[int] | None = None):
    user_ids = user_ids or [1]
    with Session(engine, expire_on_commit=False) as session:
        subscription = Subscription(
            id=subscription_id,
            type="CHANNEL",
            name="Test subscription",
            url=f"https://www.youtube.com/channel/{subscription_id}",
            avatar=None,
            description=None,
            total_videos=0,
            is_deleted=False,
            extra_data={},
            created_at=datetime(2024, 1, 1),
            updated_at=datetime(2024, 1, 1),
        )
        session.add(subscription)

        for index, user_id in enumerate(user_ids, start=1):
            if session.get(User, user_id) is None:
                session.add(
                    User(
                        id=user_id,
                        nickname=f"user-{user_id}",
                        avatar=None,
                        created_at=datetime(2024, 1, 1),
                        updated_at=datetime(2024, 1, 1),
                    ),
                )
            session.add(
                UserSubscription(
                    id=index,
                    user_id=user_id,
                    subscription_id=subscription_id,
                    is_deleted=False,
                    is_nsfw=False,
                    created_at=datetime(2024, 1, 1),
                    updated_at=datetime(2024, 1, 1),
                ),
            )

        session.add(
            SubscriptionSyncState(
                subscription_id=subscription_id,
                site="youtube",
                sync_mode="incremental",
                sync_status="queued",
                cursor_payload={},
                next_sync_at=datetime(2024, 1, 1, 1, 0, 0),
                queued_at=datetime(2024, 1, 1, 1, 0, 0),
                locked_at=datetime(2024, 1, 1, 1, 0, 0),
                pending_video_count=3,
                failure_count=0,
                idle_sync_count=0,
                version=0,
            ),
        )
        session.commit()


def test_unsubscribe_by_id_deactivates_subscription_when_last_user_leaves(engine, manage):
    _seed_subscription(engine, user_ids=[1])

    result = manage.unsubscribe_by_id(user_id=1, subscription_id=1)

    assert result is True

    with Session(engine, expire_on_commit=False) as session:
        subscription = session.get(Subscription, 1)
        user_subscription = session.query(UserSubscription).filter_by(user_id=1, subscription_id=1).one()
        sync_state = session.query(SubscriptionSyncState).filter_by(subscription_id=1).one()

    assert user_subscription.is_deleted is True
    assert subscription.is_deleted is True
    assert sync_state.sync_status == "idle"
    assert sync_state.queue_token is None
    assert sync_state.queued_at is None
    assert sync_state.locked_at is None
    assert sync_state.pending_video_count == 0
    assert sync_state.last_error == "manual_unsubscribe"


def test_unsubscribe_by_id_removes_user_feed_rows(engine, manage):
    _seed_subscription(engine, user_ids=[1])

    with Session(engine, expire_on_commit=False) as session:
        session.add(
            UserVideoFeed(
                user_id=1,
                subscription_id=1,
                video_id=99,
                publish_date=datetime(2024, 1, 1),
                video_created_at=datetime(2024, 1, 1),
                domain="youtube.com",
                is_nsfw=False,
                created_at=datetime(2024, 1, 1),
                updated_at=datetime(2024, 1, 1),
            ),
        )
        session.commit()

    result = manage.unsubscribe_by_id(user_id=1, subscription_id=1)

    assert result is True

    with Session(engine, expire_on_commit=False) as session:
        remaining_rows = session.query(UserVideoFeed).filter_by(user_id=1, subscription_id=1).all()

    assert remaining_rows == []


def test_unsubscribe_by_id_deactivates_subscription_even_when_other_users_remain(engine, manage):
    _seed_subscription(engine, user_ids=[1, 2])

    result = manage.unsubscribe_by_id(user_id=1, subscription_id=1)

    assert result is True

    with Session(engine, expire_on_commit=False) as session:
        subscription = session.get(Subscription, 1)
        removed_link = session.query(UserSubscription).filter_by(user_id=1, subscription_id=1).one()
        remaining_link = session.query(UserSubscription).filter_by(user_id=2, subscription_id=1).one()
        sync_state = session.query(SubscriptionSyncState).filter_by(subscription_id=1).one()

    assert removed_link.is_deleted is True
    assert remaining_link.is_deleted is True
    assert subscription.is_deleted is True
    assert sync_state.sync_status == "idle"
    assert sync_state.pending_video_count == 0


def test_check_subscription_status_returns_true_when_server_has_active_subscription(engine, crud):
    _seed_subscription(engine, user_ids=[2])

    result = crud.check_subscription_status(
        user_id=1,
        url="https://www.youtube.com/channel/1",
    )

    assert result == {
        "is_subscribed": True,
        "subscription_id": 1,
    }


def test_check_subscription_status_returns_false_when_subscription_is_deleted(engine, crud):
    _seed_subscription(engine, user_ids=[1])

    with Session(engine, expire_on_commit=False) as session:
        subscription = session.get(Subscription, 1)
        subscription.is_deleted = True
        session.commit()

    result = crud.check_subscription_status(
        user_id=1,
        url="https://www.youtube.com/channel/1",
    )

    assert result == {
        "is_subscribed": False,
        "subscription_id": None,
    }


def test_preview_user_subscriptions_reads_items_from_plugin_gateway(engine, session_factory):
    _seed_subscription(engine, user_ids=[1])

    with Session(engine, expire_on_commit=False) as session:
        subscription = session.get(Subscription, 1)
        subscription.url = "https://space.bilibili.com/1"
        session.commit()

    calls = []
    import_svc = SubscriptionImportService(session_factory=session_factory)

    def _fake_load_batch(site_name, *, cursor_payload=None, limit=None, gateway=None):
        calls.append({
            "site_name": site_name,
            "cursor_payload": cursor_payload,
            "limit": limit,
        })
        return SimpleNamespace(
            items=[
                SimpleNamespace(
                    url="https://space.bilibili.com/1",
                    name="Imported creator",
                    avatar="https://img/1",
                    to_dict=lambda: {"url": "https://space.bilibili.com/1", "name": "Imported creator", "avatar": "https://img/1"},
                ),
                SimpleNamespace(
                    url="https://space.bilibili.com/2",
                    name="New creator",
                    avatar="https://img/2",
                    to_dict=lambda: {"url": "https://space.bilibili.com/2", "name": "New creator", "avatar": "https://img/2"},
                ),
            ],
            total_available=2,
            has_more=False,
            cursor_payload=None,
            stop_reason=None,
        )

    import_svc._load_runtime_import_batch = _fake_load_batch

    result = import_svc.preview_user_subscriptions(site_name="bilibili", user_id=1)

    assert calls == [{
        "site_name": "bilibili",
        "cursor_payload": None,
        "limit": None,
    }]
    assert result["site"] == "bilibili"
    assert result["total"] == 2
    assert result["imported"] == 1
    assert result["not_imported"] == 1
    assert result["subscriptions"][0]["is_imported"] is True
    assert result["subscriptions"][0]["subscription_id"] == 1
    assert result["subscriptions"][1]["is_imported"] is False


def test_preview_user_subscriptions_forwards_cursor_and_limit(engine, session_factory):
    calls = []
    svc = SubscriptionImportService(session_factory=session_factory)
    svc.crud_service.get_active_user_subscription_url_map = lambda _user_id: {}

    def _fake_load_batch(site_name, *, cursor_payload=None, limit=None, gateway=None):
        calls.append({
            "site_name": site_name,
            "cursor_payload": cursor_payload,
            "limit": limit,
        })
        return SimpleNamespace(
            items=[
                SimpleNamespace(
                    url="https://javdb.com/actors/2",
                    name="Actor Two",
                    avatar=None,
                    to_dict=lambda: {"url": "https://javdb.com/actors/2", "name": "Actor Two"},
                ),
            ],
            total_available=1000,
            has_more=True,
            cursor_payload={"page": 3},
            stop_reason="batch_exhausted",
        )

    svc._load_runtime_import_batch = _fake_load_batch

    result = svc.preview_user_subscriptions(
        site_name="javdb",
        user_id=1,
        cursor_payload={"page": 2},
        limit=50,
    )

    assert calls == [{
        "site_name": "javdb",
        "cursor_payload": {"page": 2},
        "limit": 50,
    }]
    assert result["site"] == "javdb"
    assert result["total"] == 1000
    assert result["loaded"] == 1
    assert result["has_more"] is True
    assert result["cursor_payload"] == {"page": 3}
    assert result["subscriptions"][0]["url"] == "https://javdb.com/actors/2"


def test_import_user_subscriptions_uses_selected_urls_without_refetching_gateway(engine, session_factory):
    enqueued_batches = []
    svc = SubscriptionImportService(session_factory=session_factory)
    svc.crud_service.get_active_user_subscription_url_map = lambda _user_id: {}
    svc._enqueue_subscriptions_async = lambda subscriptions, user_id, site_name: enqueued_batches.append((subscriptions, user_id, site_name))

    result = svc.import_user_subscriptions(
        site_name="javdb",
        user_id=1,
        selected_urls=[
            "https://javdb.com/actors/alpha",
            "https://javdb.com/actors/beta",
        ],
        use_background_thread=False,
    )

    assert result == {
        "total": 2,
        "found": None,
        "selected": 2,
        "skipped": 0,
    }
    assert len(enqueued_batches) == 1
    queued_subscriptions, queued_user_id, queued_site_name = enqueued_batches[0]
    assert queued_user_id == 1
    assert queued_site_name == "javdb"
    assert [item.url for item in queued_subscriptions] == [
        "https://javdb.com/actors/alpha",
        "https://javdb.com/actors/beta",
    ]


def test_handle_subscribe_request_reads_subscription_meta_from_plugin_gateway(engine, session_factory):
    import_svc = SubscriptionImportService(session_factory=session_factory)
    import_svc._load_runtime_subscription_meta = staticmethod(
        lambda url, gateway=None: SimpleNamespace(
            name="Runtime channel",
            url="https://www.youtube.com/channel/UC123",
            avatar="https://img/runtime.jpg",
        ),
    )

    result = import_svc.handle_subscribe_request(
        url="https://www.youtube.com/channel/UC123",
        user_id=1,
    )

    assert result.name == "Runtime channel"
    assert result.url == "https://www.youtube.com/channel/UC123"


def test_get_runtime_supported_sites_reads_enabled_routes_from_plugin_manager(session_factory):
    registrations = [
        SimpleNamespace(capability="import_subscriptions", site_name="youtube"),
        SimpleNamespace(capability="import_subscriptions", site_name="bilibili"),
        SimpleNamespace(capability="extract_video", site_name="youtube"),
        SimpleNamespace(capability="import_subscriptions", site_name="youtube"),
    ]

    result = SubscriptionImportService.get_runtime_supported_sites(
        "import_subscriptions",
        snapshot=SimpleNamespace(registrations=registrations),
    )

    assert result == ["bilibili", "youtube"]


def test_import_user_subscriptions_filters_selected_urls_before_enqueue(engine, session_factory):
    _seed_subscription(engine, user_ids=[1])

    with Session(engine, expire_on_commit=False) as session:
        subscription = session.get(Subscription, 1)
        subscription.url = "https://space.bilibili.com/1"
        session.commit()

    enqueued_batches = []
    svc = SubscriptionImportService(session_factory=session_factory)
    svc.crud_service.get_active_user_subscription_url_map = lambda _uid: {"https://space.bilibili.com/1": 1}
    svc._enqueue_subscriptions_async = lambda subscriptions, user_id, site_name: enqueued_batches.append((subscriptions, user_id, site_name))

    result = svc.import_user_subscriptions(
        site_name="bilibili",
        user_id=1,
        selected_urls=[
            "https://space.bilibili.com/1",
            "https://space.bilibili.com/2",
        ],
        use_background_thread=False,
    )

    assert result == {
        "total": 1,
        "found": None,
        "selected": 2,
        "skipped": 1,
    }
    assert len(enqueued_batches) == 1
    queued_subscriptions, queued_user_id, queued_site_name = enqueued_batches[0]
    assert queued_user_id == 1
    assert queued_site_name == "bilibili"
    assert [item.url for item in queued_subscriptions] == ["https://space.bilibili.com/2"]


def test_import_user_subscriptions_drains_all_gateway_batches_when_no_selection(engine, session_factory):
    enqueued_batches = []
    svc = SubscriptionImportService(session_factory=session_factory)
    svc.crud_service.get_active_user_subscription_url_map = lambda _user_id: {}
    svc._enqueue_subscriptions_async = lambda subscriptions, user_id, site_name: enqueued_batches.append((subscriptions, user_id, site_name))

    svc._load_runtime_import_items = lambda site_name: [
        SimpleNamespace(url="https://javdb.com/actors/one", name="Actor One"),
        SimpleNamespace(url="https://javdb.com/actors/two", name="Actor Two"),
    ]

    result = svc.import_user_subscriptions(
        site_name="javdb",
        user_id=1,
        use_background_thread=False,
    )

    assert result == {
        "total": 2,
        "found": 2,
        "selected": 2,
        "skipped": 0,
    }
    assert len(enqueued_batches) == 1
    assert [item.url for item in enqueued_batches[0][0]] == [
        "https://javdb.com/actors/one",
        "https://javdb.com/actors/two",
    ]


def test_import_user_subscriptions_can_enqueue_synchronously(engine, session_factory):
    enqueued_batches = []
    svc = SubscriptionImportService(session_factory=session_factory)
    svc.crud_service.get_active_user_subscription_url_map = lambda _user_id: {}
    svc._load_runtime_import_items = lambda _site_name: [
        SimpleNamespace(url="https://example.com/channel/1", name="Channel 1"),
        SimpleNamespace(url="https://example.com/channel/2", name="Channel 2"),
    ]
    svc._enqueue_subscriptions_async = lambda subscriptions, user_id, site_name: enqueued_batches.append((subscriptions, user_id, site_name))

    result = svc.import_user_subscriptions(
        site_name="example",
        user_id=1,
        use_background_thread=False,
    )

    assert result == {
        "total": 2,
        "found": 2,
        "selected": 2,
        "skipped": 0,
    }
    assert len(enqueued_batches) == 1
    queued_subscriptions, queued_user_id, queued_site_name = enqueued_batches[0]
    assert queued_user_id == 1
    assert queued_site_name == "example"
    assert [item.url for item in queued_subscriptions] == [
        "https://example.com/channel/1",
        "https://example.com/channel/2",
    ]


def test_import_user_subscriptions_skips_manually_unsubscribed_urls_for_auto_import(engine, session_factory):
    _seed_subscription(engine, user_ids=[1])
    manage = SubscriptionManageService(session_factory=session_factory)

    with Session(engine, expire_on_commit=False) as session:
        subscription = session.get(Subscription, 1)
        subscription.url = "https://example.com/channel/1"
        session.commit()

    assert manage.unsubscribe_by_id(user_id=1, subscription_id=1) is True

    enqueued_batches = []
    svc = SubscriptionImportService(session_factory=session_factory)
    svc._load_runtime_import_items = lambda _site_name: [
        SimpleNamespace(url="https://example.com/channel/1", name="Channel 1"),
        SimpleNamespace(url="https://example.com/channel/2", name="Channel 2"),
    ]
    svc._enqueue_subscriptions_async = lambda subscriptions, user_id, site_name: enqueued_batches.append((subscriptions, user_id, site_name))

    result = svc.import_user_subscriptions(
        site_name="example",
        user_id=1,
        use_background_thread=False,
        respect_manual_unsubscribe=True,
    )

    assert result == {
        "total": 1,
        "found": 2,
        "selected": 2,
        "skipped": 1,
    }
    assert len(enqueued_batches) == 1
    assert [item.url for item in enqueued_batches[0][0]] == ["https://example.com/channel/2"]


def test_import_user_subscriptions_allows_manual_reimport_of_unsubscribed_urls(engine, session_factory):
    _seed_subscription(engine, user_ids=[1])
    manage = SubscriptionManageService(session_factory=session_factory)

    with Session(engine, expire_on_commit=False) as session:
        subscription = session.get(Subscription, 1)
        subscription.url = "https://example.com/channel/1"
        session.commit()

    assert manage.unsubscribe_by_id(user_id=1, subscription_id=1) is True

    enqueued_batches = []
    svc = SubscriptionImportService(session_factory=session_factory)
    svc._load_runtime_import_items = lambda _site_name: [
        SimpleNamespace(url="https://example.com/channel/1", name="Channel 1"),
    ]
    svc._enqueue_subscriptions_async = lambda subscriptions, user_id, site_name: enqueued_batches.append((subscriptions, user_id, site_name))

    result = svc.import_user_subscriptions(
        site_name="example",
        user_id=1,
        use_background_thread=False,
    )

    assert result == {
        "total": 1,
        "found": 1,
        "selected": 1,
        "skipped": 0,
    }
    assert len(enqueued_batches) == 1
    assert [item.url for item in enqueued_batches[0][0]] == ["https://example.com/channel/1"]


def test_auto_import_missing_subscriptions_imports_each_enabled_site_for_each_user(session_factory):
    svc = SubscriptionImportService(session_factory=session_factory)
    svc.manage_service.list_user_ids = lambda: [1, 2]
    svc.get_runtime_supported_sites = staticmethod(lambda capability: ["youtube", "bilibili", "disabled"])
    svc.get_enabled_runtime_import_sites = staticmethod(lambda: ["youtube", "bilibili"])

    calls = []
    svc.import_user_subscriptions = lambda site_name, user_id, selected_urls=None, *, use_background_thread=True, respect_manual_unsubscribe=False: (
        calls.append((site_name, user_id, use_background_thread, respect_manual_unsubscribe))
        or {
            "total": 1,
            "skipped": 2,
        }
    )

    result = svc.auto_import_missing_subscriptions()

    assert calls == [
        ("youtube", 1, False, True),
        ("bilibili", 1, False, True),
        ("youtube", 2, False, True),
        ("bilibili", 2, False, True),
    ]
    assert result == {
        "users": 2,
        "sites": 2,
        "imported": 4,
        "skipped": 8,
        "failed": 0,
    }


def test_list_subscriptions_search_supports_domain_and_type_tokens(engine, list_svc):
    _seed_subscription(engine, user_ids=[1])

    with Session(engine, expire_on_commit=False) as session:
        session.add(
            Subscription(
                id=2,
                type="PLAYLIST",
                name="Bilibili Playlist",
                url="https://www.bilibili.com/list/2",
                avatar=None,
                description="Playlist library",
                total_videos=0,
                is_deleted=False,
                extra_data={},
                created_at=datetime(2024, 1, 2),
                updated_at=datetime(2024, 1, 2),
            ),
        )
        session.add(
            UserSubscription(
                id=2,
                user_id=1,
                subscription_id=2,
                is_deleted=False,
                is_nsfw=False,
                created_at=datetime(2024, 1, 2),
                updated_at=datetime(2024, 1, 2),
            ),
        )
        session.commit()

    subscriptions, total = list_svc.list_subscriptions(
        user_id=1,
        query="site:bilibili type:playlist",
        type=None,
        nsfw="all",
        page=1,
        page_size=10,
    )

    assert total == 1
    assert [item["id"] for item in subscriptions] == [2]


def test_list_subscriptions_nsfw_filter_yes(engine, list_svc):
    """Verify that nsfw='yes' returns only NSFW items (showNsfw is True in config)."""
    _seed_subscription(engine, user_ids=[1])

    with Session(engine, expire_on_commit=False) as session:
        user_subscription = session.query(UserSubscription).filter_by(user_id=1, subscription_id=1).one()
        user_subscription.is_nsfw = True
        session.commit()

    subscriptions, total = list_svc.list_subscriptions(
        user_id=1,
        query=None,
        type=None,
        nsfw="yes",
        page=1,
        page_size=10,
    )

    assert total == 1
    assert subscriptions[0]["is_nsfw"] is True


def test_list_subscriptions_prefers_actual_extract_count_when_total_videos_is_stale(engine, list_svc):
    _seed_subscription(engine, user_ids=[1])

    with Session(engine, expire_on_commit=False) as session:
        subscription = session.get(Subscription, 1)
        subscription.total_videos = 1
        session.add_all([
            Video(
                id=101,
                title="Video 101",
                url="https://www.youtube.com/watch?v=101",
                domain="youtube.com",
                duration=120,
                thumbnail="https://img.example.com/101.jpg",
                publish_date=datetime(2024, 1, 2),
                created_at=datetime(2024, 1, 2),
                updated_at=datetime(2024, 1, 2),
                is_deleted=False,
            ),
            Video(
                id=102,
                title="Video 102",
                url="https://www.youtube.com/watch?v=102",
                domain="youtube.com",
                duration=120,
                thumbnail="https://img.example.com/102.jpg",
                publish_date=datetime(2024, 1, 3),
                created_at=datetime(2024, 1, 3),
                updated_at=datetime(2024, 1, 3),
                is_deleted=False,
            ),
            SubscriptionVideo(subscription_id=1, video_id=101),
            SubscriptionVideo(subscription_id=1, video_id=102),
        ])
        session.commit()

    subscriptions, total = list_svc.list_subscriptions(
        user_id=1,
        query=None,
        type=None,
        nsfw="all",
        page=1,
        page_size=10,
    )

    assert total == 1
    assert subscriptions[0]["total_extract"] == 2
    assert subscriptions[0]["total_videos"] == 2


def test_list_subscriptions_only_counts_extracts_for_current_page(engine, session_factory):
    from domains.subscription.application.services.core.listing import service as subscription_list_service_mod

    _seed_subscription(engine, user_ids=[1])

    with Session(engine, expire_on_commit=False) as session:
        session.add(
            Subscription(
                id=2,
                type="CHANNEL",
                name="Second subscription",
                url="https://www.youtube.com/channel/second",
                avatar=None,
                description=None,
                total_videos=0,
                is_deleted=False,
                extra_data={},
                created_at=datetime(2024, 1, 2),
                updated_at=datetime(2024, 1, 2),
            ),
        )
        session.add(
            UserSubscription(
                id=2,
                user_id=1,
                subscription_id=2,
                is_deleted=False,
                is_nsfw=False,
                created_at=datetime(2024, 1, 2),
                updated_at=datetime(2024, 1, 2),
            ),
        )
        session.commit()

    captured_ids = []
    svc = SubscriptionListService(session_factory=session_factory, get_user_config=_get_user_config)

    def fake_load_subscription_extract_counts(_session, subscription_ids):
        captured_ids.append(list(subscription_ids))
        return dict.fromkeys(subscription_ids, 0)

    original_load_subscription_extract_counts = subscription_list_service_mod.load_subscription_extract_counts
    subscription_list_service_mod.load_subscription_extract_counts = fake_load_subscription_extract_counts

    try:
        subscriptions, total = svc.list_subscriptions(
            user_id=1,
            query=None,
            type=None,
            nsfw="all",
            page=1,
            page_size=1,
        )
    finally:
        subscription_list_service_mod.load_subscription_extract_counts = original_load_subscription_extract_counts

    assert total == 2
    assert [item["id"] for item in subscriptions] == [2]
    assert captured_ids == [[2]]


def test_list_subscriptions_uses_lightweight_serializer_without_dto_validation(engine, list_svc):
    _seed_subscription(engine, user_ids=[1])

    with Session(engine, expire_on_commit=False) as session:
        session.add_all([
            Video(
                id=301,
                title="Video 301",
                url="https://www.youtube.com/watch?v=301",
                domain="youtube.com",
                duration=120,
                thumbnail="https://img.example.com/301.jpg",
                publish_date=datetime(2024, 1, 2),
                created_at=datetime(2024, 1, 2),
                updated_at=datetime(2024, 1, 2),
                is_deleted=False,
            ),
            SubscriptionVideo(subscription_id=1, video_id=301),
        ])
        session.commit()

    subscriptions, total = list_svc.list_subscriptions(
        user_id=1,
        query=None,
        type=None,
        nsfw="all",
        page=1,
        page_size=10,
    )

    assert total == 1


def test_list_subscriptions_recent_videos_include_source_url(engine, list_svc):
    _seed_subscription(engine, user_ids=[1])

    with Session(engine, expire_on_commit=False) as session:
        session.add(
            Video(
                id=401,
                title="Video 401",
                url="https://www.youtube.com/watch?v=401",
                domain="youtube.com",
                duration=120,
                thumbnail="https://img.example.com/401.jpg",
                publish_date=datetime(2024, 1, 4),
                created_at=datetime(2024, 1, 4),
                updated_at=datetime(2024, 1, 4),
                is_deleted=False,
            ),
        )
        session.add(SubscriptionVideo(subscription_id=1, video_id=401))
        session.commit()

    subscriptions, total = list_svc.list_subscriptions(
        user_id=1,
        query=None,
        type=None,
        nsfw="all",
        page=1,
        page_size=10,
    )

    assert total == 1
    assert subscriptions[0]["recent_videos"][0]["id"] == 401
    assert subscriptions[0]["recent_videos"][0]["url"] == "https://www.youtube.com/watch?v=401"
    assert subscriptions[0]["total_videos"] == 1
    assert subscriptions[0]["total_extract"] == 1
    assert subscriptions[0]["site"] == "youtube"
    assert subscriptions[0]["sync_status"] == "queued"
    assert subscriptions[0]["recent_videos"][0]["title"] == "Video 401"
    assert subscriptions[0]["recent_videos"][0]["duration"] == 120


def test_get_subscription_detail_prefers_actual_extract_count_when_total_videos_is_stale(engine, list_svc):
    _seed_subscription(engine, user_ids=[1])

    with Session(engine, expire_on_commit=False) as session:
        subscription = session.get(Subscription, 1)
        subscription.total_videos = 1
        session.add_all([
            Video(
                id=201,
                title="Video 201",
                url="https://www.youtube.com/watch?v=201",
                domain="youtube.com",
                duration=120,
                thumbnail="https://img.example.com/201.jpg",
                publish_date=datetime(2024, 1, 2),
                created_at=datetime(2024, 1, 2),
                updated_at=datetime(2024, 1, 2),
                is_deleted=False,
            ),
            Video(
                id=202,
                title="Video 202",
                url="https://www.youtube.com/watch?v=202",
                domain="youtube.com",
                duration=120,
                thumbnail="https://img.example.com/202.jpg",
                publish_date=datetime(2024, 1, 3),
                created_at=datetime(2024, 1, 3),
                updated_at=datetime(2024, 1, 3),
                is_deleted=False,
            ),
            SubscriptionVideo(subscription_id=1, video_id=201),
            SubscriptionVideo(subscription_id=1, video_id=202),
        ])
        session.commit()

    detail = list_svc.get_subscription_detail(1)

    assert detail.total_extract == 2
    assert detail.total_videos == 2


def test_list_subscriptions_orders_special_followed_first_and_filters(engine, list_svc):
    _seed_subscription(engine, user_ids=[1])

    with Session(engine, expire_on_commit=False) as session:
        user_subscription = session.query(UserSubscription).filter_by(user_id=1, subscription_id=1).one()
        user_subscription.is_special_followed = True
        session.add(
            Subscription(
                id=2,
                type="CHANNEL",
                name="New regular subscription",
                url="https://www.youtube.com/channel/2",
                avatar=None,
                description=None,
                total_videos=0,
                is_deleted=False,
                extra_data={},
                created_at=datetime(2024, 1, 2),
                updated_at=datetime(2024, 1, 2),
            ),
        )
        session.add(
            UserSubscription(
                id=2,
                user_id=1,
                subscription_id=2,
                is_deleted=False,
                is_nsfw=False,
                created_at=datetime(2024, 1, 2),
                updated_at=datetime(2024, 1, 2),
            ),
        )
        session.commit()

    subscriptions, total = list_svc.list_subscriptions(
        user_id=1,
        query=None,
        type=None,
        nsfw="all",
        page=1,
        page_size=10,
    )

    assert total == 2
    assert [item["id"] for item in subscriptions] == [1, 2]
    assert subscriptions[0]["is_special_followed"] is True

    special_subscriptions, special_total = list_svc.list_subscriptions(
        user_id=1,
        query=None,
        type=None,
        nsfw="all",
        page=1,
        page_size=10,
        special="yes",
    )

    assert special_total == 1
    assert [item["id"] for item in special_subscriptions] == [1]


def test_toggle_special_follow_status_updates_user_subscription(engine, manage):
    _seed_subscription(engine, user_ids=[1])

    assert manage.toggle_special_follow_status(
        user_id=1,
        subscription_id=1,
        is_special_followed=True,
    ) is True

    with Session(engine, expire_on_commit=False) as session:
        user_subscription = session.query(UserSubscription).filter_by(user_id=1, subscription_id=1).one()

    assert user_subscription.is_special_followed is True
