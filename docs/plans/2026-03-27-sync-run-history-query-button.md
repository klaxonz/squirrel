# Sync Run History Query Button Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a manual query button for sync run history filters and stop auto-fetch on every filter change.

**Architecture:** Introduce local draft filters in the run history panel. Submit the full draft to the parent only when the query button is clicked. Keep parent-owned filters as the source of truth for applied state and leave pagination immediate.

**Tech Stack:** Vue 3, Vite, Tailwind utilities, existing sync center composables

---

### Task 1: Add explicit query submission for run history filters

**Files:**
- Modify: `squirrel-frontend/src/components/sync-center/SyncRunHistoryPanel.vue`
- Modify: `squirrel-frontend/src/components/sync-center/SyncAnalysisWorkspace.vue`
- Modify: `squirrel-frontend/src/views/SyncCenter.vue`

**Step 1: Add local draft filter state**

Keep a local draft copy of all run history filters and sync it from props when parent-applied filters change.

**Step 2: Add the query button**

Place a `查询` button beside the date range picker and use the existing loading state to disable it during fetch.

**Step 3: Remove immediate auto-fetch**

Update filter controls so they only mutate local draft values until `查询` is clicked.

**Step 4: Keep existing flows**

Do not change:
- page next/prev behavior
- parent-driven date range updates
- selected run behavior

**Step 5: Verify**

Run: `npm run build:check`

Expected:
- `vue-tsc --noEmit` passes
- `vite build` passes
