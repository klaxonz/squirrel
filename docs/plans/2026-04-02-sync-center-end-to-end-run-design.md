# Sync Center End-to-End Run Design

**Status:** Approved

**Date:** 2026-04-02

**Goal:** Turn the current split "subscription feed sync + downstream video extraction" pipeline into one user-facing end-to-end sync run so the Sync Center can clearly show what is running now, how much work is done, and what is queued next.

**Non-Goals:**
- Do not replace the existing queue/runtime architecture in this change.
- Do not merge `subscription_sync` and `video_extract` into one physical worker task.
- Do not redesign unrelated dashboard pages.

---

## Problem

The current backend pipeline is operationally split:

- `subscription_sync` fetches the subscription feed and enqueues video extraction tasks
- `video_extract` runs later in a separate async path

But the current run model marks the sync run as complete as soon as feed fetching and enqueueing finish. That creates a UI mismatch:

- a run can show `success` while extraction is still ongoing
- the sync center cannot answer "which subscription is still crawling now?"
- queue visibility is weak because run completion does not represent end-to-end completion

This is not primarily a rendering problem. The data model is exposing the wrong lifecycle boundary.

---

## Chosen Approach

Keep execution physically split, but make the run lifecycle logically unified.

Rules:

- one sync run starts when a subscription sync request is created
- feed fetch, delta calculation, enqueueing, and extraction all belong to the same run
- the run does not complete when videos are merely enqueued
- the run completes only when feed work is finished and `pending_video_count == 0`

This preserves the current runtime topology while fixing the user-visible semantics.

---

## Backend Model Changes

### Run projection

Extend `subscription_sync_run_projection` so it can represent end-to-end progress instead of only feed-sync progress.

New fields:

- `feed_completed: bool`
- `has_more_pages: bool`
- `queue_position: int | None`
- `source_video_count: int | None`

Derived progress model:

- phase: `queued`, `fetching_feed`, `calculating_delta`, `enqueueing`, `extracting`, `finalizing`, `completed`, `failed`
- counts: `videos_found`, `videos_enqueued`, `videos_extracted`, `videos_skipped`, `pending_video_count`
- progress percentage:
  - while feed phase is active: percentage is phase-driven, not count-driven
  - after feed phase is done: extraction progress is based on `videos_enqueued - pending_video_count`
  - when feed is complete and pending reaches zero: 100%

### Subscription projection

The subscription-level projection should remain the main source for "what is this subscription doing now?" but its status must stay active while extraction is still draining.

Rules:

- `current_status` remains `running` after feed fetch if extraction is still pending
- `current_phase` transitions to `extracting` after enqueue completes
- only move to `success` when feed is complete and pending is zero

### Queue position

Expose deterministic queue ordering for queued subscription sync runs by ordering queued run projections on:

1. `queued_at`
2. `subscription_id`

The UI only needs stable relative order, not exact worker-internal scheduling guarantees.

---

## Event Semantics

The event stream already contains most counters. This change mainly fixes terminal-state timing and adds one explicit bridge between feed and extraction.

Required behavior:

- feed completion records `feed_completed = true`
- continuation batches for full sync keep the same `run_id`
- extraction events continue incrementing `videos_extracted`
- when extraction drains the last pending item for a run whose feed is complete, emit a terminal completion event

Important semantic change:

- `mark_sync_success(...)` can no longer mean "feed sync succeeded"
- it must mean "the end-to-end run is complete"

Introduce a non-terminal feed-finalized update path instead of using terminal success too early.

---

## API Changes

### Sync center items

Return richer per-subscription operational data:

- `run_id`
- `current_phase`
- `queue_position`
- `feed_completed`
- `has_more_pages`
- `videos_found`
- `videos_enqueued`
- `videos_extracted`
- `videos_skipped`
- `pending_video_count`
- `progress_percent`
- `progress_label`

### Sync runs

Return the same progress-oriented fields for active and historical runs so the frontend does not have to reconstruct progress from raw events.

### Overview

Keep existing summary counts, but center the page on:

- running subscriptions
- queued subscriptions
- recently finished/failed subscriptions

---

## Frontend Design

The sync center should switch from "signal dashboard first" to "operations board first".

Top-level layout:

- Running Now
- Queue
- Recent Outcomes

### Running Now

Each card shows:

- subscription identity
- current phase
- count summary: found / enqueued / extracted / pending
- progress bar with percent
- latest activity time
- direct action to open detailed run

### Queue

Each row shows:

- queue position
- subscription identity
- queued time
- mode
- pending estimate if known

### Recent Outcomes

Compact list of recent completed and failed runs for context, without competing with active work.

---

## Tradeoffs

### Why not physically merge the tasks?

A real single long-running task would:

- hold worker slots for too long
- worsen retry granularity
- make partial progress recovery harder

The user needs unified visibility, not necessarily unified execution.

### Why expose queue position as approximate order?

Exact worker scheduling order may still vary under retries and concurrency, but stable ordering by `queued_at` is enough to make the queue legible.

---

## Acceptance Criteria

- A run is not marked complete while extraction is still pending.
- The sync center can show which subscriptions are actively crawling right now.
- The sync center can show count-based progress for active runs.
- The sync center can show queue order for queued subscriptions.
- The subscription-level status remains active until end-to-end work is actually done.
