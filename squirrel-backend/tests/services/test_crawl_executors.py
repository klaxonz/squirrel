from types import SimpleNamespace

from models.crawl_task import CrawlTask
from services.crawl_executors.subscription_sync_executor import CrawlExecutorService as SubscriptionSyncExecutor
from services.crawl_executors.video_extract_executor import CrawlExecutorService as VideoExtractExecutor
from services.subscription_update.models import SubscriptionUpdateResult, UpdateMode, UpdateTrigger


def test_execute_video_extract_task_builds_dto_from_task_payload(monkeypatch):
    calls = []

    monkeypatch.setattr(
        "services.crawl_executors.video_extract_executor.extract_video",
        lambda params: calls.append(params) or SimpleNamespace(success=True),
    )

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

    result = VideoExtractExecutor.execute_video_extract_task(task)

    assert result.success is True
    assert len(calls) == 1
    assert calls[0].url == "https://www.youtube.com/watch?v=demo"
    assert calls[0].run_id == "run-1"


def test_execute_video_extract_task_raises_when_extraction_result_is_failed(monkeypatch):
    monkeypatch.setattr(
        "services.crawl_executors.video_extract_executor.extract_video",
        lambda params: SimpleNamespace(success=False, error="extract_failed"),
    )

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
        VideoExtractExecutor.execute_video_extract_task(task)
    except ValueError as exc:
        assert str(exc) == "extract_failed"
    else:
        raise AssertionError("Expected execute_video_extract_task to raise ValueError for failed extraction result")


def test_execute_subscription_sync_task_builds_request_from_payload(monkeypatch):
    calls = []
    claims = []
    monkeypatch.setattr(
        "services.crawl_executors.subscription_sync_executor.subscription_sync_state_service.claim_sync_state",
        lambda sync_state_id, queue_token, **kwargs: claims.append((sync_state_id, queue_token, kwargs)) or SimpleNamespace(
            id=sync_state_id,
            site="bilibili",
            sync_mode="full",
            pending_video_count=0,
            cursor_payload={"page": 2},
            last_seen_video_url="https://example.com/old",
        ),
    )
    monkeypatch.setattr(
        "services.crawl_executors.subscription_sync_executor.orchestrator.update",
        lambda request: calls.append(request) or SubscriptionUpdateResult(
            subscription_id=request.subscription_id,
            success=True,
            videos_found=3,
            videos_enqueued=2,
        ),
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

    result = SubscriptionSyncExecutor.execute_subscription_sync_task(task)

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


def test_execute_subscription_sync_task_uses_subscription_url_fallback(monkeypatch):
    monkeypatch.setattr(
        "services.crawl_executors.subscription_sync_executor.subscription_service.get_subscription_by_id",
        lambda subscription_id: SimpleNamespace(url="https://www.youtube.com/channel/demo"),
    )
    monkeypatch.setattr(
        "services.crawl_executors.subscription_sync_executor.orchestrator.update",
        lambda request: SubscriptionUpdateResult(
            subscription_id=request.subscription_id,
            success=True,
            videos_found=0,
            videos_enqueued=0,
        ),
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

    result = SubscriptionSyncExecutor.execute_subscription_sync_task(task)

    assert result.success is True
