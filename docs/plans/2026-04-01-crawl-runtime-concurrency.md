# Crawl Runtime Concurrency Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace single-task crawl workers with per-process execution slots and make crawl task claiming quota-safe across processes.

**Architecture:** A worker process runs one crawl runtime coordinator thread backed by a thread pool. Atomic claim uses database row locks on task rows plus dispatch scope rows so site and task-type quotas remain correct across processes.

**Tech Stack:** Python, SQLAlchemy ORM, PostgreSQL row locking, ThreadPoolExecutor, pytest

---

### Task 1: Add Dispatch Scope Persistence

**Files:**
- Create: `squirrel-backend/models/crawl_dispatch_scope.py`
- Modify: `squirrel-backend/alembic/versions/0f7c3b2a91de_add_crawl_job_and_task_tables.py`

**Step 1: Write the failing test**

Add a dispatcher/task-service test that requires claim to work when scope rows exist and when they must be created lazily.

**Step 2: Run test to verify it fails**

Run: `pipenv run pytest tests/services/test_crawl_dispatcher_service.py -q`

**Step 3: Write minimal implementation**

Add the dispatch scope model and migration/backfill support.

**Step 4: Run test to verify it passes**

Run: `pipenv run pytest tests/services/test_crawl_dispatcher_service.py -q`

### Task 2: Make Claim Atomic Across Processes

**Files:**
- Modify: `squirrel-backend/services/crawl_dispatcher/service.py`
- Modify: `squirrel-backend/services/crawl_tasks/service.py`
- Test: `squirrel-backend/tests/services/test_crawl_dispatcher_service.py`

**Step 1: Write the failing test**

Add a test that proves blocked site or task-type quotas do not get over-claimed when runtime concurrency increases.

**Step 2: Run test to verify it fails**

Run: `pipenv run pytest tests/services/test_crawl_dispatcher_service.py -q`

**Step 3: Write minimal implementation**

Lock task rows plus matching site/task-type scope rows, then evaluate counts and lease atomically.

**Step 4: Run test to verify it passes**

Run: `pipenv run pytest tests/services/test_crawl_dispatcher_service.py -q`

### Task 3: Replace Per-Task Worker Threads With Slots

**Files:**
- Modify: `squirrel-backend/core/config.py`
- Modify: `squirrel-backend/processes/managers/crawl_worker_manager.py`
- Modify: `squirrel-backend/processes/managers/crawl_worker_runtime.py`
- Test: `squirrel-backend/tests/processes/test_crawl_worker_manager.py`
- Test: `squirrel-backend/tests/processes/test_crawl_worker_runtime.py`

**Step 1: Write the failing test**

Add a runtime test that one process can execute two tasks concurrently with two slots, and a manager test that manager starts one coordinator thread instead of one thread per slot.

**Step 2: Run test to verify it fails**

Run: `pipenv run pytest tests/processes/test_crawl_worker_manager.py tests/processes/test_crawl_worker_runtime.py -q`

**Step 3: Write minimal implementation**

Introduce `CRAWL_SLOTS_PER_PROCESS`, build a thread pool inside the runtime, and let the manager start one coordinator thread.

**Step 4: Run test to verify it passes**

Run: `pipenv run pytest tests/processes/test_crawl_worker_manager.py tests/processes/test_crawl_worker_runtime.py -q`

### Task 4: Run Regression Suite

**Files:**
- Test: `squirrel-backend/tests/processes/test_crawl_worker_manager.py`
- Test: `squirrel-backend/tests/processes/test_worker_manager.py`
- Test: `squirrel-backend/tests/processes/test_crawl_worker_runtime.py`
- Test: `squirrel-backend/tests/services/test_crawl_dispatcher_service.py`
- Test: `squirrel-backend/tests/services/test_crawl_task_service.py`

**Step 1: Run targeted regression tests**

Run:

```powershell
Set-Location 'D:\Code\init\squirrel\squirrel-backend'
pipenv run pytest tests/processes/test_crawl_worker_manager.py tests/processes/test_worker_manager.py tests/processes/test_crawl_worker_runtime.py tests/services/test_crawl_dispatcher_service.py tests/services/test_crawl_task_service.py -q
```

**Step 2: Verify results**

Expected: PASS
