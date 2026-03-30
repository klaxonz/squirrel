# Subscription Full Sync Batching Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Convert full subscription sync from one blocking plugin RPC into a cursor-driven multi-batch workflow across the SDK, backend, and all runtime plugins.

**Architecture:** Extend the shared subscription sync result contract with explicit batch continuation state, then teach the backend strategy/scheduler to continue full-sync batches under one logical run, and finally migrate every plugin subscription implementation to return one bounded batch per invocation.

**Tech Stack:** Python 3.11, FastAPI backend services, Runtime V2 plugin packages, Pipenv, unittest/pytest

---

> 当前仓库约束：不引入插件侧 job/session 状态；`cursor_payload` 继续使用现有 JSON 持久化字段；实现必须保持增量同步语义不回退。

### Task 1: Lock the New Batched Contract in Shared Models

**Files:**
- Modify: `squirrel-sdk/src/crawl/core.py`
- Modify: `squirrel-sdk/src/crawl/subscription_helpers.py`
- Modify: `squirrel-backend/services/subscription_runtime_models.py`
- Modify: `squirrel-plugins/tests/test_sdk_shared_helpers.py`

**Step 1: Write the failing shared-helper test**

Add a test that proves `SubscriptionSyncResult` can carry explicit continuation state:

- `has_more=True`
- custom `cursor_payload`
- `stop_reason='batch_exhausted'`

Minimal shape:

```python
def test_build_subscription_sync_result_preserves_explicit_batch_cursor():
    result = module.build_subscription_sync_result(
        video_urls=['https://example.com/watch?v=1'],
        latest_video_url='https://example.com/watch?v=1',
        context=_Context(mode='full', cursor_payload={'page': 1}),
        stop_reason='batch_exhausted',
        cursor_payload={'page': 2},
        has_more=True,
    )
    assert result.has_more is True
    assert result.cursor_payload == {'page': 2}
```

**Step 2: Run the test to verify it fails**

Run:

```powershell
Set-Location 'D:\Code\init\squirrel'
python -m unittest squirrel-plugins.tests.test_sdk_shared_helpers
```

Expected: FAIL because `has_more` and explicit cursor override do not exist yet.

**Step 3: Implement the minimal contract update**

Change:

- `squirrel-sdk/src/crawl/core.py`
- `squirrel-backend/services/subscription_runtime_models.py`

Add `has_more: bool = False` to `SubscriptionSyncResult`.

Update `build_subscription_sync_result(...)` so callers can pass:

- `cursor_payload`
- `has_more`

without falling back to `{latest_video_url: ...}` unless explicitly desired.

**Step 4: Run the shared tests again**

Run:

```powershell
Set-Location 'D:\Code\init\squirrel'
python -m unittest squirrel-plugins.tests.test_sdk_shared_helpers
```

Expected: PASS.

**Step 5: Commit**

```powershell
git add squirrel-sdk/src/crawl/core.py squirrel-sdk/src/crawl/subscription_helpers.py squirrel-backend/services/subscription_runtime_models.py squirrel-plugins/tests/test_sdk_shared_helpers.py
git commit -m "feat: add batched subscription sync contract"
```

### Task 2: Freeze Backend Behavior for Multi-Batch Full Sync

**Files:**
- Modify: `squirrel-backend/tests/services/test_subscription_update_strategy.py`
- Modify: `squirrel-backend/tests/services/test_subscription_service.py` if shared helper coverage is needed

**Step 1: Write the failing backend tests**

Add tests covering:

- full sync batch result with `has_more=True` persists cursor and does not finalize success
- follow-up batch with `has_more=False` finalizes success
- follow-up batches reuse existing `run_id`

Minimal test ideas:

- first batch returns `video_urls=['a', 'b']`, `cursor_payload={'page': 2}`, `has_more=True`
- second batch returns `video_urls=['c']`, `cursor_payload={'page': 3}`, `has_more=False`

Assert:

- first batch schedules continuation
- first batch does not call `mark_sync_success`
- second batch does call `mark_sync_success`

**Step 2: Run the targeted backend test**

Run:

```powershell
Set-Location 'D:\Code\init\squirrel\squirrel-backend'
pipenv run pytest tests/services/test_subscription_update_strategy.py -q
```

Expected: FAIL because current strategy finalizes every successful full-sync invocation.

**Step 3: Implement minimal strategy assertions support**

Only after the failing test is in place, update the test doubles and expected payload shape so `sync_subscription` responses may include `has_more`.

Do not change production code yet beyond what the failing test needs to express.

**Step 4: Re-run the targeted backend test**

Run:

```powershell
Set-Location 'D:\Code\init\squirrel\squirrel-backend'
pipenv run pytest tests/services/test_subscription_update_strategy.py -q
```

Expected: still FAIL, but now specifically on continuation/finalization behavior.

**Step 5: Commit**

```powershell
git add squirrel-backend/tests/services/test_subscription_update_strategy.py
git commit -m "test: lock multi-batch full sync behavior"
```

### Task 3: Teach the Backend to Continue Full Sync Batches

**Files:**
- Modify: `squirrel-backend/services/subscription_update/models.py`
- Modify: `squirrel-backend/services/subscription_update/strategies/base.py`
- Modify: `squirrel-backend/services/subscription_update/strategies/default_strategy.py`
- Modify: `squirrel-backend/services/subscription_update/scheduler.py`
- Modify: `squirrel-backend/services/subscription_sync_state_service.py`

**Step 1: Implement continuation-aware result handling**

In `default_strategy.py`:

- pass batch timeout budget explicitly if needed later
- treat `has_more=True` as "continue full sync" instead of "complete full sync"

In `base.py`:

- accumulate per-batch counters
- branch between "continue" and "complete"

**Step 2: Add state update helpers for batch continuation**

In `subscription_sync_state_service.py`, add a helper that:

- persists returned `cursor_payload`
- updates per-batch metrics
- clears queue token/locks
- immediately sets next full-sync batch ready/queued state without marking success

Prefer a dedicated helper over overloading `mark_sync_success(...)`.

**Step 3: Reuse the same logical run**

In `scheduler.py` and the update request path:

- allow continuation messages to carry existing `run_id`
- ensure follow-up batches append to the same event stream

Do not create a fresh run for every batch.

**Step 4: Add explicit continuation events**

Emit events such as:

- phase changed for batch fetch/enqueue
- deferred or continued batch event with next cursor

The event names can reuse existing enums only if they remain semantically correct; otherwise add a dedicated continuation event.

**Step 5: Run targeted backend verification**

Run:

```powershell
Set-Location 'D:\Code\init\squirrel\squirrel-backend'
pipenv run pytest tests/services/test_subscription_update_strategy.py tests/plugins/test_gateway.py tests/plugins/test_supervisor_timeouts.py -q
```

Expected: PASS.

**Step 6: Commit**

```powershell
git add squirrel-backend/services/subscription_update/models.py squirrel-backend/services/subscription_update/strategies/base.py squirrel-backend/services/subscription_update/strategies/default_strategy.py squirrel-backend/services/subscription_update/scheduler.py squirrel-backend/services/subscription_sync_state_service.py squirrel-backend/tests/services/test_subscription_update_strategy.py
git commit -m "feat: continue full subscription sync in batches"
```

### Task 4: Migrate JavDB and Pornhub to Page-Based Batched Full Sync

**Files:**
- Modify: `squirrel-plugins/javdb/src/squirrel_javdb/subscription.py`
- Modify: `squirrel-plugins/pornhub/src/squirrel_pornhub/subscription.py`
- Modify: `squirrel-plugins/tests/test_subscription_sync.py`

**Step 1: Write the failing plugin tests**

Add tests that assert:

- full sync on page 1 returns `has_more=True` and `cursor_payload={'page': 2}`
- a later page can resume from `context.cursor_payload`
- final page returns `has_more=False`

Keep one-page batch boundaries explicit in the test setup.

**Step 2: Run plugin tests to verify failure**

Run:

```powershell
Set-Location 'D:\Code\init\squirrel'
python -m unittest squirrel-plugins.tests.test_subscription_sync
```

Expected: FAIL because current implementations crawl all pages in one invocation and never return `has_more`.

**Step 3: Implement JavDB batching**

In `squirrel_javdb/subscription.py`:

- read `page` from `context.cursor_payload`
- fetch only that page
- detect whether another page exists
- return next page cursor when more pages remain

**Step 4: Implement Pornhub batching**

In `squirrel_pornhub/subscription.py`:

- read `page` from `context.cursor_payload`
- fetch only that page
- derive next page from `.page_next`
- return `has_more` and next cursor accordingly

**Step 5: Re-run plugin tests**

Run:

```powershell
Set-Location 'D:\Code\init\squirrel'
python -m unittest squirrel-plugins.tests.test_subscription_sync
```

Expected: PASS.

**Step 6: Commit**

```powershell
git add squirrel-plugins/javdb/src/squirrel_javdb/subscription.py squirrel-plugins/pornhub/src/squirrel_pornhub/subscription.py squirrel-plugins/tests/test_subscription_sync.py
git commit -m "feat: batch javdb and pornhub full sync pagination"
```

### Task 5: Migrate Bilibili to Batch by Page/Resource Slice

**Files:**
- Modify: `squirrel-plugins/bilibili/src/squirrel_bilibili/subscription.py`
- Modify: `squirrel-plugins/tests/test_subscription_sync.py`

**Step 1: Write the failing Bilibili tests**

Cover:

- space subscriptions resume with page cursor
- favorite list subscriptions resume with page cursor
- channel series subscriptions resume with page cursor
- final page returns `has_more=False`

**Step 2: Run the targeted Bilibili-related tests**

Run:

```powershell
Set-Location 'D:\Code\init\squirrel'
python -m unittest squirrel-plugins.tests.test_subscription_sync
```

Expected: FAIL on Bilibili full-sync expectations.

**Step 3: Implement Bilibili batching**

In `squirrel_bilibili/subscription.py`:

- parse `page` from `context.cursor_payload`
- fetch only one page for the current resource type
- compute `has_more` from site response metadata
- return next page cursor for the next invocation

Keep incremental sync short-circuit semantics with `last_seen_video_url`.

**Step 4: Re-run the plugin tests**

Run:

```powershell
Set-Location 'D:\Code\init\squirrel'
python -m unittest squirrel-plugins.tests.test_subscription_sync
```

Expected: PASS.

**Step 5: Commit**

```powershell
git add squirrel-plugins/bilibili/src/squirrel_bilibili/subscription.py squirrel-plugins/tests/test_subscription_sync.py
git commit -m "feat: batch bilibili full sync pagination"
```

### Task 6: Migrate YouTube to Batched Slice Continuation

**Files:**
- Modify: `squirrel-plugins/youtube/src/squirrel_youtube/subscription.py`
- Modify: `squirrel-plugins/tests/test_subscription_sync.py`

**Step 1: Write the failing YouTube tests**

Because upstream iteration may not expose real page tokens, write tests for a bounded slice cursor:

- first full-sync batch returns first N deduplicated URLs and `cursor_payload={'offset': N}`
- second batch resumes from the offset
- final batch returns `has_more=False`

Use a fixed batch size constant in the plugin for deterministic tests.

**Step 2: Run the targeted YouTube-related tests**

Run:

```powershell
Set-Location 'D:\Code\init\squirrel'
python -m unittest squirrel-plugins.tests.test_subscription_sync
```

Expected: FAIL because current implementation exhausts all videos/shorts in one call.

**Step 3: Implement YouTube batching**

In `squirrel_youtube/subscription.py`:

- flatten and deduplicate current source list deterministically
- apply `offset` + `batch_size`
- return `has_more=True` when more items remain

Document this as slice-based continuation rather than native upstream pagination.

**Step 4: Re-run plugin tests**

Run:

```powershell
Set-Location 'D:\Code\init\squirrel'
python -m unittest squirrel-plugins.tests.test_subscription_sync
```

Expected: PASS.

**Step 5: Commit**

```powershell
git add squirrel-plugins/youtube/src/squirrel_youtube/subscription.py squirrel-plugins/tests/test_subscription_sync.py
git commit -m "feat: batch youtube full sync continuation"
```

### Task 7: Add Backend Continuation Safety Coverage

**Files:**
- Create: `squirrel-backend/tests/services/test_subscription_full_sync_batching.py`
- Modify: `squirrel-backend/tests/services/test_subscription_update_strategy.py`

**Step 1: Write the failing end-to-end service tests**

Cover:

- first full-sync batch queues a continuation message
- second batch on the same run completes successfully
- timeout/failure after batch 1 retries from persisted cursor rather than resetting

Prefer fake scheduler/state service stubs over real queues.

**Step 2: Run the focused backend tests**

Run:

```powershell
Set-Location 'D:\Code\init\squirrel\squirrel-backend'
pipenv run pytest tests/services/test_subscription_full_sync_batching.py tests/services/test_subscription_update_strategy.py -q
```

Expected: FAIL until continuation flow is fully wired.

**Step 3: Implement any minimal missing glue**

Only add the smallest missing production changes necessary for these tests to pass.

Avoid unrelated refactors.

**Step 4: Re-run the focused backend tests**

Run:

```powershell
Set-Location 'D:\Code\init\squirrel\squirrel-backend'
pipenv run pytest tests/services/test_subscription_full_sync_batching.py tests/services/test_subscription_update_strategy.py -q
```

Expected: PASS.

**Step 5: Commit**

```powershell
git add squirrel-backend/tests/services/test_subscription_full_sync_batching.py squirrel-backend/tests/services/test_subscription_update_strategy.py
git commit -m "test: cover full sync batch continuation"
```

### Task 8: Run Final Verification and Update Docs if Needed

**Files:**
- Modify: `docs/plans/2026-03-29-subscription-full-sync-batching-design.md` if implementation details drift
- Modify: `AGENTS.md` only if commands/workflow change

**Step 1: Run plugin verification**

Run:

```powershell
Set-Location 'D:\Code\init\squirrel'
python -m unittest squirrel-plugins.tests.test_sdk_shared_helpers squirrel-plugins.tests.test_subscription_sync squirrel-plugins.tests.test_runtime_v2_packages
```

Expected: PASS.

**Step 2: Run backend verification**

Run:

```powershell
Set-Location 'D:\Code\init\squirrel\squirrel-backend'
pipenv run pytest tests/plugins/test_gateway.py tests/plugins/test_supervisor_timeouts.py tests/services/test_subscription_update_strategy.py tests/services/test_subscription_full_sync_batching.py -q
```

Expected: PASS.

**Step 3: Run compile checks**

Run:

```powershell
Set-Location 'D:\Code\init\squirrel\squirrel-sdk'
python -m compileall src

Set-Location 'D:\Code\init\squirrel\squirrel-backend'
python -m compileall services
```

Expected: compile succeeds.

**Step 4: Commit**

```powershell
git add docs/plans/2026-03-29-subscription-full-sync-batching-design.md AGENTS.md
git commit -m "docs: finalize full sync batching rollout notes"
```
