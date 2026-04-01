# Crawl Task Unification Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace the site-scoped Redis crawl queue model with a database-backed unified task scheduler that runs `subscription_sync` and `video_extract` under one lease-based dispatcher.

**Architecture:** Introduce `crawl_job` and `crawl_task` as the durable control plane, build dispatcher and executor services around those tables, then migrate extraction and subscription sync gradually behind feature flags while shrinking Redis to a wakeup-only role.

**Tech Stack:** Python 3.11, SQLAlchemy ORM, Alembic, FastAPI backend services, Redis, Pipenv, pytest

---

> 当前仓库约束：与用户沟通使用中文；代码注释与日志保持英文；实现必须支持灰度切换；不要一次删除旧队列链路；优先保持现有 UI/事件/trace 能力不回退。

### Task 1: Add Durable Crawl Job and Task Models

**Files:**
- Create: `squirrel-backend/models/crawl_job.py`
- Create: `squirrel-backend/models/crawl_task.py`
- Modify: `squirrel-backend/models/__init__.py`
- Create: `squirrel-backend/alembic/versions/<new_revision>_add_crawl_job_and_task_tables.py`
- Test: `squirrel-backend/tests/models/test_crawl_task_models.py`

**Step 1: Write the failing model test**

Add tests for:

- job/task table creation metadata
- task default status equals `pending`
- dedupe key uniqueness expectation
- indexes needed for runnable task lookup

Minimal shape:

```python
def test_crawl_task_defaults_to_pending():
    task = CrawlTask(task_type='video_extract', site='youtube', priority='normal')
    assert task.status == 'pending'
```

**Step 2: Run test to verify it fails**

Run:

```powershell
Set-Location 'D:\Code\init\squirrel\squirrel-backend'
pipenv run pytest tests/models/test_crawl_task_models.py -q
```

Expected: FAIL because the models and migration do not exist yet.

**Step 3: Write minimal implementation**

Create `CrawlJob` and `CrawlTask` SQLAlchemy models with:

- explicit status enums or string constants
- timestamps
- foreign key from task to job
- task lookup indexes for `status`, `next_run_at`, `site`, `priority`, `lease_until`

Create the Alembic migration.

**Step 4: Run test to verify it passes**

Run:

```powershell
Set-Location 'D:\Code\init\squirrel\squirrel-backend'
pipenv run pytest tests/models/test_crawl_task_models.py -q
```

Expected: PASS.

**Step 5: Commit**

```powershell
git add squirrel-backend/models/crawl_job.py squirrel-backend/models/crawl_task.py squirrel-backend/models/__init__.py squirrel-backend/alembic/versions squirrel-backend/tests/models/test_crawl_task_models.py
git commit -m "feat: add crawl job and task models"
```

### Task 2: Build Task Store and Lease Lifecycle Services

**Files:**
- Create: `squirrel-backend/services/crawl_tasks/models.py`
- Create: `squirrel-backend/services/crawl_tasks/service.py`
- Create: `squirrel-backend/services/crawl_tasks/errors.py`
- Test: `squirrel-backend/tests/services/test_crawl_task_service.py`

**Step 1: Write the failing service tests**

Cover:

- create task and create job
- claim runnable task
- renew lease
- recover expired lease to retry state
- move terminal failures to `dead`

Minimal claim assertion:

```python
def test_claim_runnable_task_sets_lease(session):
    task = create_pending_task(session, site='youtube')
    claimed = service.claim_next_task(worker_id='worker-1')
    assert claimed.id == task.id
    assert claimed.status == 'leased'
    assert claimed.worker_id == 'worker-1'
```

**Step 2: Run test to verify it fails**

Run:

```powershell
Set-Location 'D:\Code\init\squirrel\squirrel-backend'
pipenv run pytest tests/services/test_crawl_task_service.py -q
```

Expected: FAIL because the task service does not exist.

**Step 3: Write minimal implementation**

Implement:

- `create_job(...)`
- `create_task(...)`
- `claim_task(...)`
- `start_task(...)`
- `complete_task(...)`
- `retry_task(...)`
- `fail_task(...)`
- `recover_expired_tasks(...)`

Use one atomic claim path with SQL row locking.

**Step 4: Run test to verify it passes**

Run:

```powershell
Set-Location 'D:\Code\init\squirrel\squirrel-backend'
pipenv run pytest tests/services/test_crawl_task_service.py -q
```

Expected: PASS.

**Step 5: Commit**

```powershell
git add squirrel-backend/services/crawl_tasks squirrel-backend/tests/services/test_crawl_task_service.py
git commit -m "feat: add crawl task lease service"
```

### Task 3: Add Dispatcher Fairness and Site Concurrency Control

**Files:**
- Create: `squirrel-backend/services/crawl_dispatcher/service.py`
- Create: `squirrel-backend/services/crawl_dispatcher/policy.py`
- Create: `squirrel-backend/services/crawl_dispatcher/models.py`
- Test: `squirrel-backend/tests/services/test_crawl_dispatcher_service.py`
- Modify: `squirrel-backend/core/config.py`

**Step 1: Write the failing dispatcher tests**

Cover:

- one hot site cannot consume all slots
- site quota blocks extra claims for the same site
- `subscription_sync` and `video_extract` task-type quotas both work

Minimal fairness check:

```python
def test_dispatcher_skips_site_when_site_quota_is_full(session):
    seed_running_tasks(session, site='youtube', count=2)
    seed_pending_task(session, site='youtube')
    seed_pending_task(session, site='bilibili')
    claimed = dispatcher.claim_next(worker_id='worker-1')
    assert claimed.site == 'bilibili'
```

**Step 2: Run test to verify it fails**

Run:

```powershell
Set-Location 'D:\Code\init\squirrel\squirrel-backend'
pipenv run pytest tests/services/test_crawl_dispatcher_service.py -q
```

Expected: FAIL because dispatcher policy is missing.

**Step 3: Write minimal implementation**

Implement:

- site quota lookup
- task-type quota lookup
- fair site candidate selection
- handoff to the lease service for the atomic claim

Add configuration defaults for:

- global crawl concurrency
- per-task-type concurrency
- default site concurrency

**Step 4: Run test to verify it passes**

Run:

```powershell
Set-Location 'D:\Code\init\squirrel\squirrel-backend'
pipenv run pytest tests/services/test_crawl_dispatcher_service.py -q
```

Expected: PASS.

**Step 5: Commit**

```powershell
git add squirrel-backend/services/crawl_dispatcher squirrel-backend/tests/services/test_crawl_dispatcher_service.py squirrel-backend/core/config.py
git commit -m "feat: add crawl dispatcher fairness controls"
```

### Task 4: Add Unified Executors for Subscription Sync and Video Extract

**Files:**
- Create: `squirrel-backend/services/crawl_executors/subscription_sync_executor.py`
- Create: `squirrel-backend/services/crawl_executors/video_extract_executor.py`
- Create: `squirrel-backend/services/crawl_executors/__init__.py`
- Test: `squirrel-backend/tests/services/test_crawl_executors.py`
- Modify: `squirrel-backend/services/video_extraction/extractor.py`
- Modify: `squirrel-backend/services/subscription_update/orchestrator.py`

**Step 1: Write the failing executor tests**

Cover:

- `subscription_sync` executor loads task payload and calls the orchestrator boundary
- successful sync executor creates child `video_extract` tasks
- `video_extract` executor loads task payload and drives extraction

**Step 2: Run test to verify it fails**

Run:

```powershell
Set-Location 'D:\Code\init\squirrel\squirrel-backend'
pipenv run pytest tests/services/test_crawl_executors.py -q
```

Expected: FAIL because the executors do not exist.

**Step 3: Write minimal implementation**

Extract the current queue-processor logic into reusable executors.

Rules:

- executors must not parse queue names
- executors must accept explicit task payload fields
- sync executor creates child extraction tasks via the task service
- extraction executor reuses the current extraction pipeline with minimal behavior change

**Step 4: Run test to verify it passes**

Run:

```powershell
Set-Location 'D:\Code\init\squirrel\squirrel-backend'
pipenv run pytest tests/services/test_crawl_executors.py -q
```

Expected: PASS.

**Step 5: Commit**

```powershell
git add squirrel-backend/services/crawl_executors squirrel-backend/services/video_extraction/extractor.py squirrel-backend/services/subscription_update/orchestrator.py squirrel-backend/tests/services/test_crawl_executors.py
git commit -m "feat: add unified crawl executors"
```

### Task 5: Route New Video Extraction Writes into Crawl Tasks

**Files:**
- Modify: `squirrel-backend/services/download_service.py`
- Modify: `squirrel-backend/tests/services/test_download_service.py`
- Modify: `squirrel-backend/services/subscription_sync_state_service.py`

**Step 1: Write the failing service tests**

Cover:

- enqueueing video extraction under the new flag writes one `video_extract` task
- dedupe uses the durable task store rather than only Redis keys
- legacy path still works when the flag is off

**Step 2: Run test to verify it fails**

Run:

```powershell
Set-Location 'D:\Code\init\squirrel\squirrel-backend'
pipenv run pytest tests/services/test_download_service.py -q
```

Expected: FAIL because the new task-backed path does not exist.

**Step 3: Write minimal implementation**

Under a feature flag:

- create `video_extract` tasks instead of sending to site queues
- keep the old queue path available for fallback
- store enough payload on the task to run extraction without queue-name context

Also start moving pending-count logic toward database-backed task counting.

**Step 4: Run test to verify it passes**

Run:

```powershell
Set-Location 'D:\Code\init\squirrel\squirrel-backend'
pipenv run pytest tests/services/test_download_service.py -q
```

Expected: PASS.

**Step 5: Commit**

```powershell
git add squirrel-backend/services/download_service.py squirrel-backend/services/subscription_sync_state_service.py squirrel-backend/tests/services/test_download_service.py
git commit -m "feat: route video extraction through crawl tasks"
```

### Task 6: Add Unified Crawl Worker Runtime

**Files:**
- Create: `squirrel-backend/processes/managers/crawl_worker_manager.py`
- Create: `squirrel-backend/processes/managers/crawl_worker_runtime.py`
- Test: `squirrel-backend/tests/processes/test_crawl_worker_runtime.py`
- Modify: `squirrel-backend/processes/managers/worker_manager.py`
- Modify: `squirrel-backend/queues/runner.py`

**Step 1: Write the failing runtime tests**

Cover:

- worker loop wakes up and claims tasks
- worker hands tasks to the correct executor
- worker renews leases during long-running execution

**Step 2: Run test to verify it fails**

Run:

```powershell
Set-Location 'D:\Code\init\squirrel\squirrel-backend'
pipenv run pytest tests/processes/test_crawl_worker_runtime.py -q
```

Expected: FAIL because unified worker runtime does not exist.

**Step 3: Write minimal implementation**

Implement a worker runtime that:

- polls a shared wakeup channel or timer
- asks the dispatcher for the next task
- routes to the correct executor
- renews leases
- updates task/job state on success or failure

Keep the old `WorkerRunner` in place until final cutover.

**Step 4: Run test to verify it passes**

Run:

```powershell
Set-Location 'D:\Code\init\squirrel\squirrel-backend'
pipenv run pytest tests/processes/test_crawl_worker_runtime.py -q
```

Expected: PASS.

**Step 5: Commit**

```powershell
git add squirrel-backend/processes/managers/crawl_worker_manager.py squirrel-backend/processes/managers/crawl_worker_runtime.py squirrel-backend/processes/managers/worker_manager.py squirrel-backend/queues/runner.py squirrel-backend/tests/processes/test_crawl_worker_runtime.py
git commit -m "feat: add unified crawl worker runtime"
```

### Task 7: Move Subscription Sync Scheduling into the New Job/Task Model

**Files:**
- Modify: `squirrel-backend/services/subscription_update/scheduler.py`
- Modify: `squirrel-backend/services/subscription_update/models.py`
- Modify: `squirrel-backend/tests/services/test_subscription_update_scheduler.py`
- Modify: `squirrel-backend/tests/services/test_subscription_update_strategy.py`

**Step 1: Write the failing scheduler tests**

Cover:

- scheduling a subscription sync creates one `crawl_job`
- the job owns one root `subscription_sync` task
- manual and scheduled triggers map to task priority/source correctly
- legacy queue path still exists behind the old flag

**Step 2: Run test to verify it fails**

Run:

```powershell
Set-Location 'D:\Code\init\squirrel\squirrel-backend'
pipenv run pytest tests/services/test_subscription_update_scheduler.py tests/services/test_subscription_update_strategy.py -q
```

Expected: FAIL because scheduler still pushes directly to Redis site queues.

**Step 3: Write minimal implementation**

Under a feature flag:

- create a root job/task instead of queueing directly
- preserve existing `run_id`, trace, trigger, mode metadata
- keep compatibility updates to `subscription_sync_state` during migration

**Step 4: Run test to verify it passes**

Run:

```powershell
Set-Location 'D:\Code\init\squirrel\squirrel-backend'
pipenv run pytest tests/services/test_subscription_update_scheduler.py tests/services/test_subscription_update_strategy.py -q
```

Expected: PASS.

**Step 5: Commit**

```powershell
git add squirrel-backend/services/subscription_update/scheduler.py squirrel-backend/services/subscription_update/models.py squirrel-backend/tests/services/test_subscription_update_scheduler.py squirrel-backend/tests/services/test_subscription_update_strategy.py
git commit -m "feat: schedule subscription sync through crawl jobs"
```

### Task 8: Replace Queue-Scan Backpressure with Task-Backed Counting

**Files:**
- Modify: `squirrel-backend/queues/queue_monitor.py`
- Modify: `squirrel-backend/services/subscription_sync_state_service.py`
- Test: `squirrel-backend/tests/services/test_subscription_backpressure.py`

**Step 1: Write the failing backpressure tests**

Cover:

- pending extraction count comes from task statuses instead of Redis stream scans
- counts ignore succeeded and dead tasks
- counts include `pending`, `leased`, `running`, `retry_wait`

**Step 2: Run test to verify it fails**

Run:

```powershell
Set-Location 'D:\Code\init\squirrel\squirrel-backend'
pipenv run pytest tests/services/test_subscription_backpressure.py -q
```

Expected: FAIL because current monitor scans Redis streams.

**Step 3: Write minimal implementation**

Switch the backpressure monitor and pending reconciliation paths to database-backed queries.

Keep a compatibility wrapper if callers still import `queue_monitor`.

**Step 4: Run test to verify it passes**

Run:

```powershell
Set-Location 'D:\Code\init\squirrel\squirrel-backend'
pipenv run pytest tests/services/test_subscription_backpressure.py -q
```

Expected: PASS.

**Step 5: Commit**

```powershell
git add squirrel-backend/queues/queue_monitor.py squirrel-backend/services/subscription_sync_state_service.py squirrel-backend/tests/services/test_subscription_backpressure.py
git commit -m "feat: back crawl pending counts with task queries"
```

### Task 9: Shrink Redis to Shared Wakeup and Retire Site-Scoped Consumers

**Files:**
- Modify: `squirrel-backend/queues/direct_producer.py`
- Modify: `squirrel-backend/queues/consumer_registrar.py`
- Modify: `squirrel-backend/queues/consumer_config.py`
- Modify: `squirrel-backend/queues/runner.py`
- Modify: `squirrel-backend/consumer/processors/subscription_update_task.py`
- Modify: `squirrel-backend/consumer/processors/extract_task.py`
- Test: `squirrel-backend/tests/queues/test_runner.py`

**Step 1: Write the failing queue/runtime tests**

Cover:

- no per-site consumer registration is required when V2 is fully enabled
- wakeup publishing goes to shared channels only
- old processors become unused compatibility paths

**Step 2: Run test to verify it fails**

Run:

```powershell
Set-Location 'D:\Code\init\squirrel\squirrel-backend'
pipenv run pytest tests/queues/test_runner.py -q
```

Expected: FAIL because current runtime still registers site-scoped consumers.

**Step 3: Write minimal implementation**

When both task-model flags are enabled:

- stop registering site-scoped consumers
- keep only shared wakeup channels if Redis wakeup is still needed
- make legacy processors wrappers or dead code paths scheduled for deletion

**Step 4: Run test to verify it passes**

Run:

```powershell
Set-Location 'D:\Code\init\squirrel\squirrel-backend'
pipenv run pytest tests/queues/test_runner.py -q
```

Expected: PASS.

**Step 5: Commit**

```powershell
git add squirrel-backend/queues/direct_producer.py squirrel-backend/queues/consumer_registrar.py squirrel-backend/queues/consumer_config.py squirrel-backend/queues/runner.py squirrel-backend/consumer/processors/subscription_update_task.py squirrel-backend/consumer/processors/extract_task.py squirrel-backend/tests/queues/test_runner.py
git commit -m "refactor: retire site-scoped crawl consumers"
```

### Task 10: Run Final Verification and Document Rollout Flags

**Files:**
- Modify: `docs/plans/2026-04-01-crawl-task-unification-design.md` if implementation drifts
- Modify: `AGENTS.md` only if workflow commands change
- Modify: `squirrel-backend/core/config.py` if flag docs belong there

**Step 1: Run backend verification**

Run:

```powershell
Set-Location 'D:\Code\init\squirrel\squirrel-backend'
pipenv run pytest tests/models/test_crawl_task_models.py tests/services/test_crawl_task_service.py tests/services/test_crawl_dispatcher_service.py tests/services/test_crawl_executors.py tests/services/test_download_service.py tests/services/test_subscription_update_scheduler.py tests/services/test_subscription_backpressure.py tests/processes/test_crawl_worker_runtime.py tests/queues/test_runner.py -q
```

Expected: PASS.

**Step 2: Run compile checks**

Run:

```powershell
Set-Location 'D:\Code\init\squirrel\squirrel-backend'
python -m compileall models services processes queues
```

Expected: compile succeeds.

**Step 3: Verify feature flag rollout notes**

Document and confirm the staged flags:

- `CRAWL_TASK_MODEL_ENABLED`
- `CRAWL_VIDEO_EXTRACT_V2_ENABLED`
- `CRAWL_SUBSCRIPTION_SYNC_V2_ENABLED`

**Step 4: Commit**

```powershell
git add docs/plans/2026-04-01-crawl-task-unification-design.md AGENTS.md squirrel-backend/core/config.py
git commit -m "docs: finalize crawl task unification rollout"
```
