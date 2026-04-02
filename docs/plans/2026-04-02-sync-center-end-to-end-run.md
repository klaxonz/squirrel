# Sync Center End-to-End Run Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Make Sync Center represent one end-to-end subscription crawl run from feed fetch through video extraction drain, then redesign the page so running work and queue order are obvious.

**Architecture:** Keep `subscription_sync` and `video_extract` as separate execution steps, but change projection and terminal-state rules so one shared `run_id` remains active until extraction is drained. Then update Sync Center APIs and frontend components to render running cards, queue rows, and recent outcomes from the new progress fields.

**Tech Stack:** Python backend services, SQLAlchemy ORM, FastAPI routes, Vue 3, Vite, TypeScript, Tailwind

---

### Task 1: Add failing backend tests for end-to-end run completion semantics

**Files:**
- Modify: `squirrel-backend/tests/services/test_subscription_sync_site_filters.py`
- Create: `squirrel-backend/tests/services/test_subscription_sync_end_to_end_runs.py`

**Step 1: Write the failing test**

Cover:

- feed completion with non-zero `pending_video_count` keeps run/subscription status active
- run only completes when `pending_video_count` drains to zero
- queued items expose stable queue ordering

**Step 2: Run test to verify it fails**

Run:

```powershell
Set-Location 'D:\Code\init\squirrel\squirrel-backend'
pipenv run pytest tests/services/test_subscription_sync_end_to_end_runs.py -q
```

**Step 3: Write minimal implementation**

Touch only projection/state logic needed by the failing tests.

**Step 4: Run test to verify it passes**

Run the same pytest command and confirm green.

### Task 2: Extend run and center DTO/service outputs for progress fields

**Files:**
- Modify: `squirrel-backend/schemas/subscription/dto/sync_center_dto.py`
- Modify: `squirrel-backend/services/subscription_sync_center_service.py`
- Modify: `squirrel-backend/services/subscription_sync_history_service.py`

**Step 1: Write the failing test**

Add assertions for:

- `run_id`
- `current_phase`
- `queue_position`
- `feed_completed`
- `videos_found`
- `videos_enqueued`
- `videos_extracted`
- `videos_skipped`
- `pending_video_count`
- `progress_percent`
- `progress_label`

**Step 2: Run test to verify it fails**

Run:

```powershell
Set-Location 'D:\Code\init\squirrel\squirrel-backend'
pipenv run pytest tests/services/test_subscription_sync_end_to_end_runs.py tests/services/test_subscription_sync_site_filters.py -q
```

**Step 3: Write minimal implementation**

Compute progress server-side so frontend rendering stays simple and consistent.

**Step 4: Run test to verify it passes**

Run the same pytest command and confirm green.

### Task 3: Change sync state terminal timing from feed-complete to end-to-end-complete

**Files:**
- Modify: `squirrel-backend/services/subscription_sync_state_service.py`
- Modify: `squirrel-backend/services/subscription_update/strategies/base.py`
- Modify: `squirrel-backend/services/video_extraction/extractor.py`

**Step 1: Write the failing test**

Add tests for:

- feed finalization does not emit terminal success when extraction is still pending
- last extraction completion emits terminal success for the owning run
- full-sync continuation keeps the same run active

**Step 2: Run test to verify it fails**

Run:

```powershell
Set-Location 'D:\Code\init\squirrel\squirrel-backend'
pipenv run pytest tests/services/test_subscription_sync_end_to_end_runs.py -q
```

**Step 3: Write minimal implementation**

Introduce a non-terminal feed-finalized path and defer terminal completion until the extraction drain is done.

**Step 4: Run test to verify it passes**

Run the same pytest command and confirm green.

### Task 4: Surface queue order and end-to-end progress in Sync Center composables

**Files:**
- Modify: `squirrel-frontend/src/api/subscriptionSyncCenter.ts`
- Modify: `squirrel-frontend/src/composables/useSyncCenter.ts`
- Modify: `squirrel-frontend/src/composables/useSyncHistory.ts`

**Step 1: Add the failing type/use-site expectations**

Use TypeScript typecheck failure as the red step by updating interfaces first to expect the new API fields.

**Step 2: Run typecheck to verify it fails**

Run:

```powershell
Set-Location 'D:\Code\init\squirrel\squirrel-frontend'
npm run typecheck
```

**Step 3: Write minimal implementation**

Normalize new progress fields and expose derived slices for running, queued, and recent sections.

**Step 4: Run typecheck to verify it passes**

Run the same command and confirm green.

### Task 5: Replace the current Sync Center analysis-first layout with an operations board

**Files:**
- Modify: `squirrel-frontend/src/views/SyncCenter.vue`
- Modify: `squirrel-frontend/src/components/sync-center/SyncAnalysisWorkspace.vue`
- Create: `squirrel-frontend/src/components/sync-center/SyncActiveRunBoard.vue`
- Create: `squirrel-frontend/src/components/sync-center/SyncQueueBoard.vue`
- Create: `squirrel-frontend/src/components/sync-center/SyncRecentRunBoard.vue`
- Modify: `squirrel-frontend/src/components/sync-center/SyncControlBar.vue`

**Step 1: Create the failing UI contract**

Update the page to require the new props first so build/typecheck breaks until the new board components exist.

**Step 2: Run typecheck/build to verify it fails**

Run:

```powershell
Set-Location 'D:\Code\init\squirrel\squirrel-frontend'
npm run build:check
```

**Step 3: Write minimal implementation**

Render:

- active runs with progress bars and count summaries
- queued runs with queue position
- recent completed/failed runs as compact context

Keep the detail drawer path intact.

**Step 4: Run typecheck/build to verify it passes**

Run the same command and confirm green.

### Task 6: Final verification

**Files:**
- Modify: `docs/plans/2026-04-02-sync-center-end-to-end-run-design.md` only if implementation meaning changes

**Step 1: Run backend verification**

```powershell
Set-Location 'D:\Code\init\squirrel\squirrel-backend'
pipenv run pytest tests/services/test_subscription_sync_end_to_end_runs.py tests/services/test_subscription_sync_site_filters.py -q
```

**Step 2: Run frontend verification**

```powershell
Set-Location 'D:\Code\init\squirrel\squirrel-frontend'
npm run build:check
```

**Step 3: Confirm the user-visible behavior**

Manual checklist:

- one running subscription clearly shows phase and counts
- queue section clearly shows order
- completed runs do not appear finished before extraction drain completes
