# Subscription Sync Event-Driven Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace subscription-wide periodic enqueue scans with a DB-backed event flow that emits due sync work from `subscription_sync_state`, consumes durable outbox events, and records incremental gap-suspicion signals for later full backfill decisions.

**Architecture:** Add a durable `outbox_event` table and service, emit due events from scheduler tasks by scanning `subscription_sync_state`, consume those events into existing `crawl_task` rows, and update incremental sync state with explicit gap-suspicion fields after sync execution. Keep `crawl_task + worker` as the execution layer and keep scheduled jobs as the polling fallback path.

**Tech Stack:** Python, SQLAlchemy ORM, PostgreSQL-compatible SQL patterns, existing in-repo scheduler/task framework, pytest

---

### File Map

**Create:**
- `squirrel-backend/models/outbox_event.py`
- `squirrel-backend/services/outbox_event_service.py`
- `squirrel-backend/schedule/tasks/subscription_sync_event_consumer_task.py`
- `squirrel-backend/alembic/versions/<new_revision>_add_outbox_event_and_gap_state_fields.py`
- `squirrel-backend/tests/services/test_outbox_event_service.py`

**Modify:**
- `squirrel-backend/models/subscription_sync_state.py`
- `squirrel-backend/services/subscription_sync_state_service.py`
- `squirrel-backend/services/subscription_runtime_models.py`
- `squirrel-backend/services/subscription_update/models.py`
- `squirrel-backend/services/subscription_update/strategies/base.py`
- `squirrel-backend/services/subscription_update/strategies/default_strategy.py`
- `squirrel-backend/services/subscription_update/scheduler.py`
- `squirrel-backend/schedule/tasks/subscription_incremental_update_task.py`
- `squirrel-backend/schedule/tasks/subscription_full_update_task.py`
- `squirrel-backend/tests/services/test_subscription_update_scheduler.py`
- `squirrel-backend/tests/services/test_subscription_sync_end_to_end_runs.py`

### Task 1: Add Failing Tests for Durable Outbox and Due-State Emission

**Files:**
- Create: `squirrel-backend/tests/services/test_outbox_event_service.py`
- Modify: `squirrel-backend/tests/services/test_subscription_update_scheduler.py`

- [x] **Step 1: Write failing outbox service tests**

```python
def test_publish_due_event_persists_pending_outbox_row(monkeypatch):
    event = outbox_event_service.publish_event(
        event_type='incremental_sync_due',
        event_key='incremental_sync_due:11:2026-04-04T10:00',
        aggregate_type='subscription_sync_state',
        aggregate_id='11',
        payload={'sync_state_id': 11, 'mode': 'incremental'},
    )

    assert event.status == 'pending'
    assert event.available_at is not None
```

- [x] **Step 2: Run outbox tests to verify RED**

Run: `cd squirrel-backend; pipenv run pytest tests/services/test_outbox_event_service.py -v`
Expected: FAIL because `outbox_event_service` and `OutboxEvent` do not exist yet

- [x] **Step 3: Write failing due-state scheduler tests**

```python
def test_enqueue_all_due_states_uses_state_service_instead_of_subscription_scan(monkeypatch):
    monkeypatch.setattr(
        scheduler_module.subscription_sync_state_service,
        'list_due_sync_states',
        lambda mode, limit=200: [
            (SimpleNamespace(id=11, subscription_id=1), 'https://space.bilibili.com/1'),
        ],
    )

    published = []
    monkeypatch.setattr(
        scheduler_module.outbox_event_service,
        'publish_event',
        lambda **kwargs: published.append(kwargs),
    )

    success, failed = SubscriptionScheduler().enqueue_due_states(
        trigger=UpdateTrigger.SCHEDULED,
        mode=UpdateMode.INCREMENTAL,
    )

    assert (success, failed) == (1, 0)
    assert published[0]['event_type'] == 'incremental_sync_due'
```

- [x] **Step 4: Run scheduler tests to verify RED**

Run: `cd squirrel-backend; pipenv run pytest tests/services/test_subscription_update_scheduler.py -v`
Expected: FAIL because `enqueue_due_states` and `publish_event` do not exist yet

### Task 2: Implement Outbox Model, Service, and Due-State Emission

**Files:**
- Create: `squirrel-backend/models/outbox_event.py`
- Create: `squirrel-backend/services/outbox_event_service.py`
- Modify: `squirrel-backend/services/subscription_update/scheduler.py`
- Modify: `squirrel-backend/schedule/tasks/subscription_incremental_update_task.py`
- Modify: `squirrel-backend/schedule/tasks/subscription_full_update_task.py`
- Create: `squirrel-backend/alembic/versions/<new_revision>_add_outbox_event_and_gap_state_fields.py`

- [x] **Step 1: Add the `OutboxEvent` model and migration**

```python
class OutboxEvent(Base, SerializerMixin):
    __tablename__ = 'outbox_event'

    __table_args__ = (
        UniqueConstraint('event_key', name='uix_outbox_event_key'),
        Index('ix_outbox_event_status_available', 'status', 'available_at'),
    )
```

- [x] **Step 2: Implement `publish_event()` and claim helpers**

```python
def publish_event(*, event_type: str, event_key: str, aggregate_type: str, aggregate_id: str, payload: dict, ...):
    with get_session() as session:
        event = OutboxEvent(...)
        session.add(event)
        session.flush()
        return event
```

- [x] **Step 3: Replace subscription scanning with due-state emission**

```python
def enqueue_due_states(self, trigger: UpdateTrigger, mode: UpdateMode) -> tuple[int, int]:
    due_rows = subscription_sync_state_service.list_due_sync_states(mode.value)
    for sync_state, url in due_rows:
        outbox_event_service.publish_event(
            event_type='incremental_sync_due' if mode == UpdateMode.INCREMENTAL else 'full_sync_due',
            event_key=...,
            aggregate_type='subscription_sync_state',
            aggregate_id=str(sync_state.id),
            payload={...},
        )
```

- [x] **Step 4: Wire scheduler tasks to emit events instead of direct crawl tasks**

Run: `cd squirrel-backend; pipenv run pytest tests/services/test_outbox_event_service.py tests/services/test_subscription_update_scheduler.py -v`
Expected: PASS

### Task 3: Add Event Consumer Path Into Existing Crawl Tasks

**Files:**
- Create: `squirrel-backend/schedule/tasks/subscription_sync_event_consumer_task.py`
- Modify: `squirrel-backend/services/outbox_event_service.py`

- [x] **Step 1: Write failing consumer test**

```python
def test_consume_due_event_creates_incremental_subscription_sync_task(monkeypatch):
    processed = outbox_event_service.consume_available_events(limit=10)
    assert processed['processed'] == 1
```

- [x] **Step 2: Run consumer tests to verify RED**

Run: `cd squirrel-backend; pipenv run pytest tests/services/test_outbox_event_service.py -v`
Expected: FAIL because the consumer path does not create crawl tasks yet

- [x] **Step 3: Implement handler dispatch**

```python
def handle_event(event: OutboxEvent) -> None:
    if event.event_type == 'incremental_sync_due':
        _handle_incremental_sync_due(event)
        return
    if event.event_type == 'full_sync_due':
        _handle_full_sync_due(event)
        return
```

- [x] **Step 4: Add scheduled polling consumer task**

```python
@TaskRegistry.register(interval=15, unit='seconds', start_immediately=True)
class SubscriptionSyncEventConsumerTask(BaseTask):
    @classmethod
    def run(cls):
        outbox_event_service.consume_available_events(limit=50)
```

- [x] **Step 5: Verify consumer tests**

Run: `cd squirrel-backend; pipenv run pytest tests/services/test_outbox_event_service.py tests/services/test_subscription_update_scheduler.py -v`
Expected: PASS

### Task 4: Add Gap-Suspicion State and Incremental Scoring

**Files:**
- Modify: `squirrel-backend/models/subscription_sync_state.py`
- Modify: `squirrel-backend/services/subscription_runtime_models.py`
- Modify: `squirrel-backend/services/subscription_update/models.py`
- Modify: `squirrel-backend/services/subscription_update/strategies/base.py`
- Modify: `squirrel-backend/services/subscription_update/strategies/default_strategy.py`
- Modify: `squirrel-backend/services/subscription_sync_state_service.py`
- Modify: `squirrel-backend/tests/services/test_subscription_sync_end_to_end_runs.py`

- [x] **Step 1: Write failing gap-scoring test**

```python
def test_record_gap_signals_escalates_to_full_backfill_request(monkeypatch):
    result = subscription_sync_state_service.record_gap_detection_result(
        sync_state_id=11,
        anchor_found=False,
        cursor_invalid=True,
        head_sample_urls=['https://example.com/v1'],
    )

    assert result['gap_suspicion_score'] >= 8
```

- [x] **Step 2: Run gap-scoring test to verify RED**

Run: `cd squirrel-backend; pipenv run pytest tests/services/test_subscription_sync_end_to_end_runs.py -v`
Expected: FAIL because gap state fields and scoring helper do not exist yet

- [x] **Step 3: Extend runtime result models and state fields minimally**

```python
@dataclass
class SubscriptionSyncResult:
    ...
    head_sample_urls: Optional[List[str]] = None
    anchor_found: Optional[bool] = None
    cursor_invalid: Optional[bool] = None
    cursor_loop_detected: Optional[bool] = None
```

- [x] **Step 4: Add scoring and full-backfill event emission**

```python
score += 5 if anchor_found is False else 0
score += 5 if cursor_invalid else 0
score += 5 if cursor_loop_detected else 0
if score >= 8:
    outbox_event_service.publish_event(event_type='full_backfill_requested', ...)
```

- [x] **Step 5: Verify targeted sync tests**

Run: `cd squirrel-backend; pipenv run pytest tests/services/test_subscription_sync_end_to_end_runs.py tests/services/test_subscription_update_scheduler.py tests/services/test_outbox_event_service.py -v`
Expected: PASS

### Task 5: Final Verification

**Files:**
- Verify only

- [x] **Step 1: Run the focused backend regression suite**

Run: `cd squirrel-backend; pipenv run pytest tests/services/test_outbox_event_service.py tests/services/test_subscription_update_scheduler.py tests/services/test_subscription_sync_end_to_end_runs.py tests/services/test_crawl_task_service.py tests/processes/test_crawl_worker_runtime.py -v`
Expected: PASS

- [x] **Step 2: Inspect working tree**

Run: `git status --short`
Expected: only intended backend code, tests, docs, and migration files are modified

- [ ] **Step 3: Commit**

```bash
git add squirrel-backend docs/superpowers/plans/2026-04-04-subscription-sync-event-driven.md
git commit -m "feat: add db-backed subscription sync event flow"
```
