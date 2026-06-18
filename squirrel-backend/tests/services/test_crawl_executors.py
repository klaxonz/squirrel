from types import SimpleNamespace
from unittest.mock import MagicMock

from domains.subscription.application.services.core.update.models import (
    SubscriptionUpdateResult,
    UpdateMode,
    UpdateTrigger,
)
from domains.subscription.application.services.crawl.executors.subscription_sync_executor import (
    CrawlExecutorService as SubscriptionSyncExecutor,
)
from domains.subscription.application.services.crawl.executors.video_extract_executor import (
    CrawlExecutorService as VideoExtractExecutor,
)
from domains.subscription.domain.models.crawl_task import CrawlTask


def _make_video_extract_svc(extract_video_func=None):
    return VideoExtractExecutor(
        extract_video_func=extract_video_func,
    )


def _make_sync_svc(sync_state_service=None, orchestrator_service=None, subscription_svc=None):
    return SubscriptionSyncExecutor(
        sync_state_service=sync_state_service,
        orchestrator_service=orchestrator_service,
        subscription_svc=subscription_svc,
    )


def test_execute_video_extract_task_builds_dto_from_task_payload():
    extract_video_mock = MagicMock(return_value=SimpleNamespace(success=True))

    svc = _make_video_extract_svc(extract_video_func=extract_video_mock)

    task = CrawlTask(
        job_id=1,
        task_type="video_extract",
        site="youtube.com",
        payload={
            "url": "https://www.youtube.com/watch?v=demo",
            "subscribed": True,
            "only_extract": True,
            "subscription_id": 1,
            "sync_state_id": 2,
            "run_id": "run-1",
            "trigger": "manual",
            "is_manual": True,
            "is_extract_all": False,
        },
    )

    result = svc.execute_video_extract_task(task)

    assert result.success is True
    assert extract_video_mock.call_count == 1
    params = extract_video_mock.call_args[0][0]
    assert params.url == "https://www.youtube.com/watch?v=demo"
    assert params.run_id == "run-1"


def test_execute_video_extract_task_raises_when_extraction_result_is_failed():
    extract_video_mock = MagicMock(return_value=SimpleNamespace(success=False, error="extract_failed"))

    svc = _make_video_extract_svc(extract_video_func=extract_video_mock)

    task = CrawlTask(
        job_id=1,
        task_type="video_extract",
        site="youtube.com",
        payload={
            "url": "https://www.youtube.com/watch?v=demo",
            "subscribed": True,
            "only_extract": True,
            "subscription_id": 1,
        },
    )

    try:
        svc.execute_video_extract_task(task)
    except ValueError as exc:
        assert str(exc) == "extract_failed"
    else:
        raise AssertionError("Expected execute_video_extract_task to raise ValueError for failed extraction result")


def test_execute_subscription_sync_task_builds_request_from_payload():
    claims = []

    class FakeSyncStateService:
        @staticmethod
        def claim_sync_state(sync_state_id, queue_token, **kwargs):
            claims.append((sync_state_id, queue_token, kwargs))
            return SimpleNamespace(
                id=sync_state_id,
                site="bilibili",
                sync_mode="full",
                pending_video_count=0,
                cursor_payload={"page": 2},
                last_seen_video_url="https://example.com/old",
            )

    calls = []

    class FakeOrchestrator:
        @staticmethod
        def update(request):
            calls.append(request)
            return SubscriptionUpdateResult(
                subscription_id=request.subscription_id,
                success=True,
                videos_found=3,
                videos_enqueued=2,
            )

    svc = _make_sync_svc(
        sync_state_service=FakeSyncStateService,
        orchestrator_service=FakeOrchestrator,
    )

    task = CrawlTask(
        job_id=1,
        task_type="subscription_sync",
        site="bilibili",
        payload={
            "subscription_id": 10,
            "url": "https://space.bilibili.com/42",
            "trigger": "manual",
            "mode": "full",
            "user_id": 5,
            "force": True,
            "trace_id": "trace-1",
            "request_id": "req-1",
            "run_id": "run-1",
            "sync_state_id": 99,
            "queue_token": "queue-1",
            "cursor_payload": {"page": 2},
            "last_seen_video_url": "https://example.com/old",
            "inline_video_extraction": True,
        },
    )

    result = svc.execute_subscription_sync_task(task)

    assert result.success is True
    assert claims == [
        (
            99,
            "queue-1",
            {
                "run_id": "run-1",
                "request_id": "req-1",
                "trace_id": "trace-1",
                "trigger": "manual",
            },
        ),
    ]
    assert len(calls) == 1
    assert calls[0].subscription_id == 10
    assert calls[0].url == "https://space.bilibili.com/42"
    assert calls[0].trigger == UpdateTrigger.MANUAL
    assert calls[0].mode == UpdateMode.FULL
    assert calls[0].cursor_payload == {"page": 2}
    assert calls[0].last_seen_video_url == "https://example.com/old"
    assert calls[0].inline_video_extraction is True


def test_execute_subscription_sync_task_uses_subscription_url_fallback():
    class FakeSubscriptionService:
        @staticmethod
        def get_subscription_by_id(subscription_id):
            return SimpleNamespace(url="https://www.youtube.com/channel/demo")

    class FakeOrchestrator:
        @staticmethod
        def update(request):
            return SubscriptionUpdateResult(
                subscription_id=request.subscription_id,
                success=True,
                videos_found=0,
                videos_enqueued=0,
            )

    svc = _make_sync_svc(
        subscription_svc=FakeSubscriptionService,
        orchestrator_service=FakeOrchestrator,
    )

    task = CrawlTask(
        job_id=1,
        task_type="subscription_sync",
        site="youtube",
        payload={
            "subscription_id": 7,
            "trigger": "scheduled",
            "mode": "incremental",
        },
    )

    result = svc.execute_subscription_sync_task(task)

    assert result.success is True
