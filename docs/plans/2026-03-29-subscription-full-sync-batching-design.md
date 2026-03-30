# Subscription Full Sync Batching Design

**Status:** Approved

**Date:** 2026-03-29

**Goal:** Replace the current "one blocking `sync_subscription` RPC per full sync" model with a cursor-driven batched protocol that keeps each plugin invocation bounded while preserving one logical full-sync run in backend state and UI.

**Non-Goals:**
- Do not introduce plugin-side long-lived job/session state.
- Do not redesign the subscription update queue topology.
- Do not change the user-facing meaning of incremental sync.

---

## Problem

Current full sync behavior is architecturally unstable:

- Backend treats `sync_subscription` as one blocking RPC in `squirrel-backend/services/subscription_update/strategies/default_strategy.py`.
- Plugin implementations for Bilibili, JavDB, Pornhub, and YouTube iterate pages/items until the whole subscription is exhausted.
- Runtime timeout therefore scales with channel size and network variability rather than with a bounded unit of work.
- A timeout failure restarts the whole channel scan from the last persisted state instead of retrying only the current page/batch.

This means no fixed timeout can be correct for all subscriptions. Large channels will always push the model past its safe operating envelope.

---

## Chosen Approach

Use stateless cursor-driven batching for all subscription plugins.

The contract becomes:

- Each `sync_subscription` invocation processes exactly one bounded batch.
- The plugin receives `context.cursor_payload` and decides where to resume.
- The plugin returns:
  - `video_urls`
  - `latest_video_url`
  - `cursor_payload`
  - `stop_reason`
  - `has_more`
  - `source_video_count`
  - `total_available`
- `cursor_payload` represents the next position to resume from, not a summary of the last batch.
- Backend persists the returned cursor after every successful batch.
- Backend only marks the full sync successful when `has_more == false`.
- If `has_more == true`, backend schedules the next batch immediately using the same logical sync run.

This keeps the protocol stateless across plugin invocations while allowing each plugin to express pagination in its own native cursor shape.

---

## Why Not Plugin-Side Job State

We explicitly reject a plugin-side scan job/session model for now.

Reasons:

- It introduces lifecycle complexity around `job_id`, cleanup, runtime restarts, cancellation, and leak prevention.
- A runtime crash would require recovery semantics for in-memory plugin jobs.
- Existing backend state already has a durable cursor field and sync-state lifecycle.
- The current problem is bounded work per invocation, which stateless batching already solves.

Stateless cursor-based continuation gives most of the operational benefit with much lower complexity.

---

## Data Model Changes

### SDK

`squirrel-sdk/src/crawl/core.py`

- Add `has_more: bool = False` to `SubscriptionSyncResult`.
- Keep `cursor_payload` as the next-batch cursor.
- Keep `stop_reason` for observability and diagnostics rather than control flow.

`squirrel-sdk/src/crawl/subscription_helpers.py`

- Update `build_subscription_sync_result(...)` so it can build batched results without assuming cursor payload is only `{latest_video_url: ...}`.
- Keep `append_subscription_video_url(...)` for dedupe and incremental cursor-hit logic, but stop using `limit=None` as the full-sync control model.

### Backend

`squirrel-backend/services/subscription_runtime_models.py`

- Mirror the SDK-side `has_more` field.

`squirrel-backend/models/subscription_sync_state.py`

- No schema change is required if `cursor_payload` remains JSON.
- The meaning of `cursor_payload` changes to "next batch cursor".

---

## Protocol Semantics

### Incremental Sync

- Usually finishes in one invocation.
- May still return `has_more == false` immediately.
- `last_seen_video_url` remains valid for stopping when an already-known item is reached.

### Full Sync

- Must no longer read the entire subscription in one call.
- Each invocation processes one page or one bounded item batch.
- `cursor_payload` determines the next page/token/offset.
- When the source is exhausted, the plugin returns `has_more == false` and a terminal `stop_reason` such as `source_exhausted`.

### Cursor Rules

- Cursor shape is plugin-specific.
- Examples:
  - Bilibili: `{"kind": "space", "page": 3}`
  - JavDB: `{"page": 4, "sort_type": 0}`
  - Pornhub: `{"page": 6}`
  - YouTube: `{"offset": 200}` or a playlist/channel-specific token
- Backend treats the cursor as opaque JSON.

---

## Backend Flow

### Current

1. Scheduler enqueues one full-sync task.
2. Strategy calls plugin once.
3. Plugin scans entire subscription.
4. Backend marks sync success/failure based on that one RPC.

### New

1. Scheduler enqueues one full-sync task.
2. Strategy calls plugin once for the current cursor.
3. Plugin returns one batch plus `has_more`.
4. Backend enqueues extracted videos for that batch.
5. Backend persists the returned cursor.
6. If `has_more == true`:
   - keep the same logical run open
   - schedule the next full-sync batch immediately
   - do not call `mark_sync_success`
7. If `has_more == false`:
   - mark sync success
   - persist final cursor/latest item metadata
   - complete the run

This changes full sync from a long RPC into a resumable multi-message workflow.

---

## Run and Event Semantics

The full sync must still appear as one logical run to users.

Requirements:

- The first queued batch creates the run as today.
- Follow-up batches reuse the same `run_id`.
- Event stream must distinguish:
  - batch queued
  - batch fetched
  - batch enqueued
  - batch continued
  - full sync completed
- Aggregate counters such as `videos_found` and `videos_enqueued` must accumulate across batches rather than overwrite on each batch.

This avoids a UX regression where a large full sync looks like repeated disconnected runs.

---

## Failure and Retry Model

- Timeout or transient failure only invalidates the current batch.
- Retry starts from the last durable `cursor_payload`, not from the beginning of the channel.
- Duplicates remain safe because backend enqueue already skips known videos and blocked videos.
- A stale running recovery still works because the durable cursor always points to the next incomplete batch.

This gives bounded retry cost even for very large subscriptions.

---

## Plugin Migration Strategy

All plugins must move to the new protocol:

- `squirrel-plugins/bilibili/src/squirrel_bilibili/subscription.py`
- `squirrel-plugins/javdb/src/squirrel_javdb/subscription.py`
- `squirrel-plugins/pornhub/src/squirrel_pornhub/subscription.py`
- `squirrel-plugins/youtube/src/squirrel_youtube/subscription.py`

Migration guidance:

- Use one source page or one bounded item slice as a batch.
- Return `has_more == true` whenever another page/slice remains.
- Ensure returned cursor always points to the next unread segment.
- Preserve incremental semantics using `last_seen_video_url`.

---

## Timeout Model After Migration

After batching, timeout should only reflect one batch budget.

That means:

- Manifest timeout for `sync_subscription` becomes a per-batch timeout.
- It no longer needs to scale with channel size.
- Different sites may still need different budgets, but the problem becomes operational tuning rather than architectural failure.

---

## Risks

### Cursor correctness

If a plugin returns the wrong next cursor, full sync can skip or repeat pages.

Mitigation:

- Add per-plugin pagination regression tests.
- Keep cursor payload explicit and site-shaped.

### Aggregate run accounting

If backend still calls `mark_sync_success` on every batch, UI/history will become incorrect.

Mitigation:

- Introduce explicit continue-vs-complete branching in the update strategy.
- Add backend tests for multi-batch full sync accumulation.

### YouTube pagination constraints

YouTube channel/playlist libraries may not expose native page tokens in the same way as HTML-based sites.

Mitigation:

- Start with a bounded slice cursor if true upstream pagination is not exposed.
- Keep the cursor opaque so the plugin can evolve independently.

---

## Acceptance Criteria

- No full sync relies on one unbounded plugin RPC.
- Every subscription plugin returns bounded batched `sync_subscription` results.
- Backend persists next-batch cursor after each successful batch.
- A full sync with multiple batches appears as one logical run.
- Timeout retry resumes from the last successful batch cursor.
- Existing incremental sync behavior remains correct.
