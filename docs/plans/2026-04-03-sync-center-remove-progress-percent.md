# Sync Center Remove Progress Percent Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Remove low-value percent indicators and Feed progress bars from Sync Center cards while keeping phase/status and count metrics.

**Architecture:** This is a frontend-only presentation change in three board components. No API or backend projection changes are needed because existing phase labels and count fields already cover the remaining UI.

**Tech Stack:** Vue 3 SFC, TypeScript setup scripts, existing Sync Center composables.

---

### Task 1: Simplify Active Run Cards

**Files:**
- Modify: `squirrel-frontend/src/components/sync-center/SyncActiveRunBoard.vue`

**Step 1: Remove percent and progress bar rendering**
- Delete the right-side percent text and the progress rail/fill block.
- Keep `progress_label` and phase/count chips.

**Step 2: Remove now-unused helpers/styles**
- Drop `showPercent`, `showProgressRail`, and related CSS classes.

### Task 2: Simplify Recent Cards

**Files:**
- Modify: `squirrel-frontend/src/components/sync-center/SyncRecentRunBoard.vue`
- Modify: `squirrel-frontend/src/components/sync-center/SyncRecentTaskBoard.vue`

**Step 1: Remove right-side percent blocks**
- Keep status chips, timestamps, and metric pills.

**Step 2: Remove summary-percent styles**
- Drop unused summary/percent CSS classes.

### Task 3: Verify

**Files:**
- Test: `squirrel-frontend/src/utils/syncCenterHistoryWindow.test.mjs`
- Test: `squirrel-frontend/src/utils/syncRunProgressDisplay.test.mjs`
- Test: `squirrel-frontend/test/sync-center-feed-dashboard-snapshot.test.mjs`
- Test: `squirrel-frontend/test/sync-center-shared-refresh-clock.test.mjs`
- Test: `squirrel-frontend/test/sync-feed-recent-lane.test.mjs`

**Step 1: Run targeted frontend tests**
- `node squirrel-frontend/src/utils/syncCenterHistoryWindow.test.mjs`
- `node squirrel-frontend/src/utils/syncRunProgressDisplay.test.mjs`
- `node squirrel-frontend/test/sync-center-feed-dashboard-snapshot.test.mjs`
- `node squirrel-frontend/test/sync-center-shared-refresh-clock.test.mjs`
- `node squirrel-frontend/test/sync-feed-recent-lane.test.mjs`

**Expected:** All commands pass.
