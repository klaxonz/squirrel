from contextlib import contextmanager
from datetime import datetime, timedelta
from pathlib import Path
import sys

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from models import Base
from models.links import UserSubscription
from models.subscription import Subscription
from models.subscription_sync_run_projection import SubscriptionSyncRunProjection
from models.subscription_sync_state import SubscriptionSyncState
from models.subscription_sync_subscription_projection import SubscriptionSyncSubscriptionProjection
from services import subscription_sync_center_service, subscription_sync_history_service, subscription_sync_state_service


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


def _setup_projection_env(monkeypatch):
    engine = create_engine('sqlite:///:memory:')
    Base.metadata.create_all(
        engine,
        tables=[
            Subscription.__table__,
            UserSubscription.__table__,
            SubscriptionSyncRunProjection.__table__,
            SubscriptionSyncSubscriptionProjection.__table__,
        ],
    )
    monkeypatch.setattr(subscription_sync_center_service, 'get_session', lambda: _managed_session(engine))
    monkeypatch.setattr(subscription_sync_history_service, 'get_session', lambda: _managed_session(engine))
    return engine


def _setup_state_env(monkeypatch):
    engine = create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine, tables=[SubscriptionSyncState.__table__])
    monkeypatch.setattr(subscription_sync_state_service, 'get_session', lambda: _managed_session(engine))
    return engine


def _seed_projection_data(engine):
    now = datetime(2026, 4, 2, 11, 0, 0)
    with Session(engine, expire_on_commit=False) as session:
        session.add_all([
            Subscription(
                id=1,
                type='CHANNEL',
                name='Running Channel',
                url='https://www.youtube.com/channel/running',
                avatar=None,
                description=None,
                total_videos=0,
                is_deleted=False,
                extra_data={},
                created_at=now,
                updated_at=now,
            ),
            Subscription(
                id=4,
                type='CHANNEL',
                name='Running Earlier',
                url='https://www.youtube.com/channel/earlier',
                avatar=None,
                description=None,
                total_videos=0,
                is_deleted=False,
                extra_data={},
                created_at=now,
                updated_at=now,
            ),
            Subscription(
                id=2,
                type='CHANNEL',
                name='Queued First',
                url='https://space.bilibili.com/queued-1',
                avatar=None,
                description=None,
                total_videos=0,
                is_deleted=False,
                extra_data={},
                created_at=now,
                updated_at=now,
            ),
            Subscription(
                id=3,
                type='CHANNEL',
                name='Queued Second',
                url='https://space.bilibili.com/queued-2',
                avatar=None,
                description=None,
                total_videos=0,
                is_deleted=False,
                extra_data={},
                created_at=now,
                updated_at=now,
            ),
        ])
        session.add_all([
            UserSubscription(id=1, user_id=1, subscription_id=1, is_deleted=False, is_nsfw=False, created_at=now, updated_at=now),
            UserSubscription(id=4, user_id=1, subscription_id=4, is_deleted=False, is_nsfw=False, created_at=now, updated_at=now),
            UserSubscription(id=2, user_id=1, subscription_id=2, is_deleted=False, is_nsfw=False, created_at=now, updated_at=now),
            UserSubscription(id=3, user_id=1, subscription_id=3, is_deleted=False, is_nsfw=False, created_at=now, updated_at=now),
        ])
        session.add_all([
            SubscriptionSyncRunProjection(
                run_id='run-running-earlier',
                subscription_id=4,
                sync_state_id=104,
                site='youtube.com',
                sync_mode='incremental',
                trigger='manual',
                request_id='req-running-earlier',
                trace_id='trace-running-earlier',
                status='running',
                current_phase='extracting',
                queued_at=now - timedelta(minutes=6),
                started_at=now - timedelta(minutes=5),
                finished_at=None,
                duration_ms=0,
                failure_count=0,
                error_type=None,
                error_message=None,
                videos_found=6,
                videos_enqueued=5,
                videos_extracted=1,
                videos_skipped=1,
                pending_video_count=4,
                last_event_seq_no=7,
                last_event_at=now - timedelta(minutes=1),
                created_at=now - timedelta(minutes=6),
                updated_at=now - timedelta(minutes=1),
            ),
            SubscriptionSyncRunProjection(
                run_id='run-running',
                subscription_id=1,
                sync_state_id=101,
                site='youtube.com',
                sync_mode='incremental',
                trigger='manual',
                request_id='req-running',
                trace_id='trace-running',
                status='running',
                current_phase='extracting',
                queued_at=now - timedelta(minutes=3),
                started_at=now - timedelta(minutes=2),
                finished_at=None,
                duration_ms=0,
                failure_count=0,
                error_type=None,
                error_message=None,
                videos_found=10,
                videos_enqueued=8,
                videos_extracted=5,
                videos_skipped=2,
                pending_video_count=3,
                last_event_seq_no=8,
                last_event_at=now,
                created_at=now - timedelta(minutes=3),
                updated_at=now,
            ),
            SubscriptionSyncRunProjection(
                run_id='run-queued-1',
                subscription_id=2,
                sync_state_id=102,
                site='bilibili.com',
                sync_mode='incremental',
                trigger='scheduled',
                request_id='req-queued-1',
                trace_id='trace-queued-1',
                status='queued',
                current_phase='queued',
                queued_at=now - timedelta(minutes=4),
                started_at=None,
                finished_at=None,
                duration_ms=0,
                failure_count=0,
                error_type=None,
                error_message=None,
                videos_found=0,
                videos_enqueued=0,
                videos_extracted=0,
                videos_skipped=0,
                pending_video_count=0,
                last_event_seq_no=2,
                last_event_at=now - timedelta(minutes=4),
                created_at=now - timedelta(minutes=4),
                updated_at=now - timedelta(minutes=4),
            ),
            SubscriptionSyncRunProjection(
                run_id='run-queued-2',
                subscription_id=3,
                sync_state_id=103,
                site='bilibili.com',
                sync_mode='full',
                trigger='scheduled',
                request_id='req-queued-2',
                trace_id='trace-queued-2',
                status='queued',
                current_phase='queued',
                queued_at=now - timedelta(minutes=1),
                started_at=None,
                finished_at=None,
                duration_ms=0,
                failure_count=0,
                error_type=None,
                error_message=None,
                videos_found=0,
                videos_enqueued=0,
                videos_extracted=0,
                videos_skipped=0,
                pending_video_count=0,
                last_event_seq_no=2,
                last_event_at=now - timedelta(minutes=1),
                created_at=now - timedelta(minutes=1),
                updated_at=now - timedelta(minutes=1),
            ),
        ])
        session.add_all([
            SubscriptionSyncSubscriptionProjection(
                subscription_id=4,
                latest_run_id='run-running-earlier',
                current_status='running',
                current_phase='extracting',
                last_sync_at=now - timedelta(minutes=5),
                last_success_at=None,
                next_sync_at=now + timedelta(minutes=8),
                last_error_message=None,
                pending_video_count=4,
                failure_streak=0,
                last_event_seq_no=7,
                updated_at=now - timedelta(minutes=1),
            ),
            SubscriptionSyncSubscriptionProjection(
                subscription_id=1,
                latest_run_id='run-running',
                current_status='running',
                current_phase='extracting',
                last_sync_at=now - timedelta(minutes=2),
                last_success_at=None,
                next_sync_at=now + timedelta(minutes=10),
                last_error_message=None,
                pending_video_count=3,
                failure_streak=0,
                last_event_seq_no=8,
                updated_at=now,
            ),
            SubscriptionSyncSubscriptionProjection(
                subscription_id=2,
                latest_run_id='run-queued-1',
                current_status='queued',
                current_phase='queued',
                last_sync_at=now - timedelta(hours=1),
                last_success_at=now - timedelta(hours=1),
                next_sync_at=now,
                last_error_message=None,
                pending_video_count=0,
                failure_streak=0,
                last_event_seq_no=2,
                updated_at=now - timedelta(minutes=4),
            ),
            SubscriptionSyncSubscriptionProjection(
                subscription_id=3,
                latest_run_id='run-queued-2',
                current_status='queued',
                current_phase='queued',
                last_sync_at=now - timedelta(hours=2),
                last_success_at=now - timedelta(hours=2),
                next_sync_at=now,
                last_error_message=None,
                pending_video_count=0,
                failure_streak=0,
                last_event_seq_no=2,
                updated_at=now - timedelta(minutes=1),
            ),
        ])
        session.commit()


def test_sync_center_items_expose_progress_fields_and_queue_position(monkeypatch):
    engine = _setup_projection_env(monkeypatch)
    _seed_projection_data(engine)

    running_result = subscription_sync_center_service.list_sync_center_items(
        user_id=1,
        status='running',
        site=None,
        query=None,
        page=1,
        page_size=20,
    )
    queued_result = subscription_sync_center_service.list_sync_center_items(
        user_id=1,
        status='queued',
        site=None,
        query=None,
        page=1,
        page_size=20,
    )
    runs_result = subscription_sync_history_service.list_runs(user_id=1, status='running', page=1, page_size=20)

    assert [item.subscription_name for item in running_result.data] == ['Running Earlier', 'Running Channel']

    running_item = running_result.data[1]
    assert running_item.run_id == 'run-running'
    assert running_item.current_phase == 'extracting'
    assert running_item.feed_completed is True
    assert running_item.videos_found == 10
    assert running_item.videos_enqueued == 8
    assert running_item.videos_extracted == 5
    assert running_item.videos_skipped == 2
    assert running_item.pending_video_count == 3
    assert running_item.progress_percent == 62
    assert running_item.progress_label == '5 / 8'

    assert [item.subscription_name for item in queued_result.data] == ['Queued First', 'Queued Second']
    assert [item.queue_position for item in queued_result.data] == [1, 2]

    assert runs_result['data'][0]['run_id'] == 'run-running'
    assert runs_result['data'][0]['progress_percent'] == 62
    assert runs_result['data'][0]['feed_completed'] is True


def test_mark_sync_success_stays_running_until_pending_videos_are_drained(monkeypatch):
    engine = _setup_state_env(monkeypatch)
    captured_events = []
    monkeypatch.setattr(subscription_sync_state_service, 'append_event', lambda event, session=None: captured_events.append(event))

    now = datetime(2026, 4, 2, 12, 0, 0)
    with Session(engine, expire_on_commit=False) as session:
        session.add(
            SubscriptionSyncState(
                id=11,
                subscription_id=1,
                site='youtube.com',
                sync_mode='incremental',
                sync_status='running',
                cursor_payload={'cursor': 'done'},
                last_seen_video_url='https://example.com/video/1',
                last_sync_at=now - timedelta(minutes=1),
                last_success_at=None,
                next_sync_at=now + timedelta(minutes=5),
                queued_at=now - timedelta(minutes=2),
                locked_at=now - timedelta(minutes=2),
                queue_token='queue-token',
                pending_video_count=3,
                failure_count=0,
                idle_sync_count=0,
                version=0,
                last_error=None,
                created_at=now - timedelta(hours=1),
                updated_at=now - timedelta(minutes=2),
            )
        )
        session.commit()

    subscription_sync_state_service.mark_sync_success(
        11,
        cursor_payload={'cursor': 'done'},
        latest_video_url='https://example.com/video/1',
        source_video_count=10,
        videos_found=10,
        videos_enqueued=8,
        run_id='run-1',
        request_id='req-1',
        trace_id='trace-1',
        trigger='manual',
    )

    with Session(engine, expire_on_commit=False) as session:
        state = session.get(SubscriptionSyncState, 11)

    assert state.sync_status == 'running'
    assert state.locked_at is None
    assert state.pending_video_count == 3
    assert state.last_success_at is None
    assert [event.event_type for event in captured_events] == ['phase_changed']
    assert captured_events[-1].event_phase == 'extracting'

    subscription_sync_state_service.decrement_pending_video_count(
        11,
        count=3,
        run_id='run-1',
        request_id='req-1',
        trace_id='trace-1',
        trigger='manual',
    )

    with Session(engine, expire_on_commit=False) as session:
        state = session.get(SubscriptionSyncState, 11)

    assert state.sync_status == 'success'
    assert state.pending_video_count == 0
    assert state.last_success_at is not None
    assert [event.event_type for event in captured_events] == ['phase_changed', 'completed']
