# Subscription Sync Event-Driven Design

Date: 2026-04-04
Status: Proposed and user-approved for planning
Scope: `squirrel-backend`

## Context

The current subscription crawl flow already separates scheduling from execution:

- The scheduler enqueues `subscription_sync` crawl tasks.
- Workers execute `subscription_sync` and `video_extract` tasks from the DB-backed crawl task store.
- `subscription_sync_state` already tracks `next_sync_at`, backpressure, retry timing, and terminal reconciliation.

This is better than a direct cron-driven crawler, but the scheduling layer still has three structural problems:

1. It still performs due-task discovery by scanning active subscriptions instead of treating sync state as the source of truth.
2. Incremental and full syncs still compete through the same scheduling entrance, which allows full sync work to interfere with incremental freshness.
3. Historical gap detection is too implicit. Incremental sync can suspect missing history, but the decision model is not explicit or budgeted.

## Goals

1. Reduce unnecessary scans and scheduling work.
2. Keep incremental freshness within 5-10 minutes at the current scale of 1000+ subscriptions and 10k+ video tasks per hour.
3. Keep full sync as a required fallback path without allowing it to starve incremental sync.
4. Avoid Redis and keep the design DB-first.
5. Preserve at-least-once delivery with idempotent consumers.
6. Reuse the existing DB task queue, worker runtime, and sync state machinery as much as possible.

## Non-Goals

1. Replace the existing `crawl_task` execution model.
2. Introduce Kafka, Temporal, Celery, or a new external message broker.
3. Guarantee exactly-once processing.
4. Remove periodic full sync fallback in the short term.

## Recommendation

Adopt a PostgreSQL-first event-driven scheduling model:

- `subscription_sync_state` remains the scheduling truth source.
- A new `outbox_event` table stores domain events durably.
- `LISTEN/NOTIFY` is used only as a wake-up accelerator.
- Consumers still read durable events from PostgreSQL using `FOR UPDATE SKIP LOCKED`.
- Existing `crawl_task` and worker processes remain the execution substrate.
- The scheduler process is reduced to due emission, recovery, reconciliation, and low-frequency full-sync guard work.

This is intentionally a hybrid design. It upgrades scheduling to event-driven behavior without replacing the stable DB task execution path.

## Why This Approach

### Alternative A: keep the current scheduler and improve scanning

Pros:

- Lowest change risk.
- Fastest implementation.

Cons:

- Still mainly time-driven.
- State changes still wait for the next polling cycle.
- Full and incremental orchestration remain tightly coupled.

### Alternative B: PostgreSQL outbox with `LISTEN/NOTIFY` and polling fallback

Pros:

- Durable events stay in PostgreSQL.
- No Redis dependency.
- Lower latency than pure polling.
- Natural fit with the current DB task claim model.

Cons:

- More moving parts than the current scheduler.
- Requires strict idempotency and recovery design.

### Alternative C: full workflow engine or external MQ

Pros:

- Highest long-term orchestration ceiling.

Cons:

- Highest migration and operational cost.
- Not justified yet by current scale and existing architecture maturity.

Recommended choice: Alternative B.

## Target Architecture

### Core components

1. `subscription_sync_state`
   - Keeps `next_sync_at`, sync status, retry/backoff data, pending counters, and gap suspicion state.
   - Remains the source of truth for whether a subscription is due.

2. `outbox_event`
   - Stores durable domain events.
   - Supports delayed delivery, retries, dead-letter handling, and observability.

3. `event_consumer`
   - Listens for database notifications.
   - Claims pending events from `outbox_event` with `FOR UPDATE SKIP LOCKED`.
   - Dispatches work to specialized handlers.

4. `crawl_task`
   - Remains the execution queue for `subscription_sync` and `video_extract`.
   - Continues to use existing worker and dispatcher logic.

5. `scheduler`
   - Stops acting as the main scheduling brain.
   - Only emits due events and runs periodic recovery or fallback jobs.

### High-level flow

```text
subscription_sync_state -> due emitter -> outbox_event
outbox_event -> event consumer -> crawl_task
crawl_task -> worker runtime -> plugin/site execution
worker results -> outbox_event -> projection/update handlers -> subscription_sync_state
```

## Event Model

### First event set

The first implementation should keep the event set intentionally small:

- `incremental_sync_due`
- `incremental_sync_completed`
- `incremental_sync_failed`
- `full_backfill_requested`
- `full_sync_due`
- `video_extract_completed`
- `sync_reconcile_requested`

### Event table fields

`outbox_event` should include:

- `id`
- `event_type`
- `event_key`
- `aggregate_type`
- `aggregate_id`
- `payload`
- `status` (`pending`, `processing`, `done`, `dead`)
- `priority`
- `available_at`
- `attempt_count`
- `max_attempts`
- `locked_by`
- `locked_at`
- `last_error`
- `created_at`
- `processed_at`

### Event key strategy

Examples:

- `incremental_sync_due:{sync_state_id}:{time_bucket}`
- `full_backfill_requested:{subscription_id}:{reason}:{day_bucket}`

Event handling must be designed for at-least-once delivery. Duplicate event delivery is acceptable if handlers remain idempotent.

## Incremental Sync Flow

1. A due-emitter task queries `subscription_sync_state` for incremental states with `next_sync_at <= now`.
2. For each due state, it writes `incremental_sync_due` into `outbox_event`.
3. An event consumer claims the event and validates:
   - the state is not already `queued` or `running`
   - incremental backpressure does not exceed limits
   - the event is not superseded by a newer state transition
4. If valid, the handler creates an incremental `subscription_sync` crawl task.
5. A worker executes the task and emits:
   - `incremental_sync_completed`, or
   - `incremental_sync_failed`
6. The completion handler updates sync state, next schedule time, and historical gap signals.
7. If gap suspicion crosses threshold, the handler emits `full_backfill_requested`.

## Full Sync Flow

Full sync stays in the system, but it must become a budgeted fallback lane instead of competing directly with incremental freshness.

### Full sync trigger sources

- First-time subscription bootstrap
- Incremental gap suspicion
- Low-frequency periodic fallback
- Manual trigger

### Full sync flow

1. Any trigger source emits `full_backfill_requested`.
2. A full-backfill handler checks:
   - whether a full sync is already `queued` or `running`
   - whether a recent full request already exists
   - whether site-level and global full-sync budget is available
3. If budget is not available, the event is delayed by updating `available_at`.
4. If budget is available, the handler emits `full_sync_due`.
5. A dedicated handler creates a low-priority full `subscription_sync` crawl task.
6. On success, the full-sync completion path:
   - updates `total_available`
   - clears gap suspicion state
   - sets the next full sync time

## Historical Gap Detection

Incremental sync cannot prove the absence of history gaps. It can only accumulate strong signals that history is likely missing.

### State fields to add

Add to incremental sync state:

- `last_seen_video_url`
- `last_head_sample_urls`
- `last_head_fingerprint`
- `last_known_total_available`
- `gap_suspicion_score`
- `gap_suspicion_reason`
- `last_gap_detected_at`
- `last_full_requested_at`
- `head_anchor_missing_count`

### Plugin result fields to add

Extend `SubscriptionSyncResult` with optional fields:

- `head_sample_urls`
- `anchor_found`
- `oldest_scanned_url`
- `cursor_invalid`
- `cursor_loop_detected`
- `scan_depth`
- `total_available`

Plugins provide signals. Scheduling logic decides whether to escalate.

### Gap suspicion scoring

Initial scoring model:

- missing `last_seen_video_url` anchor: `+5`
- invalid cursor: `+5`
- cursor loop or repeated page loop: `+5`
- low overlap with previous head sample: `+3`
- significant source total vs local total drift: `+2`
- repeated anchor misses: additional `+2`
- anchor found: `-4`
- healthy head overlap: `-2`
- successful full sync: reset score to `0`

### Escalation thresholds

- `0-4`: no action
- `5-7`: record suspicion only
- `8-9`: emit low-priority `full_backfill_requested`
- `>=10`: emit high-priority `full_backfill_requested`

Guardrails:

- do not emit another full request if full sync is already queued or running
- do not emit repeated full requests within 24 hours unless manual override is used

## Resource Isolation

Incremental freshness is the primary SLA. Full sync must have a strictly separated budget.

Recommended first cut:

- full sync global concurrency: `1-2`
- per-site full sync concurrency: `1`
- full sync share of total sync capacity: at most `10%-20%`
- priority order:
  - manual full
  - gap-triggered full
  - periodic fallback full

If needed, a later iteration can split `subscription_sync` into distinct runtime task types for incremental and full execution to make dispatcher policy simpler.

## Consumer and Recovery Model

### Consumption

- Consumers use `LISTEN/NOTIFY` for wake-up only.
- Consumers claim real work from `outbox_event`.
- Claiming must use `FOR UPDATE SKIP LOCKED`.

### Retry

On handler failure:

- increment `attempt_count`
- set a delayed `available_at`
- leave event in `pending` until `max_attempts` is reached
- mark as `dead` after retry exhaustion

### Recovery

Keep the following periodic recovery jobs:

1. requeue stale `processing` outbox events
2. recover stale queued or running sync states
3. reconcile terminal sync states against `video_extract` task reality
4. emit periodic full fallback requests at low frequency

## Migration Plan

### Phase 1: state-driven due discovery

- Replace active-subscription scanning with due-state scanning.
- Keep the rest of the scheduling flow unchanged.

### Phase 2: add durable event infrastructure

- Introduce `outbox_event`.
- Start writing events for observability only.
- Do not switch orchestration yet.

### Phase 3: eventize incremental sync

- Add `incremental_sync_due` consumer path.
- Convert incremental task creation to event-driven handling.
- Add plugin result fields and gap suspicion scoring.

### Phase 4: eventize full backfill

- Add `full_backfill_requested` and `full_sync_due`.
- Enforce separate full-sync budget.

### Phase 5: shrink scheduler responsibilities

- Keep only due emission, recovery, reconciliation, and periodic fallback full guard jobs.

## Risks

1. Duplicate event delivery
   - Mitigation: event keys, idempotent handlers, task dedupe keys

2. Missed database notifications
   - Mitigation: polling fallback over `outbox_event`

3. Over-triggering full sync for weak sites
   - Mitigation: site capability tiers and conservative thresholds

4. Full sync starving incremental sync
   - Mitigation: explicit concurrency and budget isolation

5. Event flow becoming hard to debug
   - Mitigation: aggregate IDs, event timeline queries, dead-event visibility

## Open Implementation Decisions

1. Whether to split incremental and full runtime tasks into separate `task_type` values immediately or later.
2. Whether `last_head_sample_urls` should live in `subscription_sync_state` or a small auxiliary detail table.
3. Whether low-capability sites need custom gap-scoring profiles.
4. Whether `LISTEN/NOTIFY` should be handled in the existing scheduler process or in a dedicated consumer process.

## Rollout Success Criteria

1. Incremental due detection no longer scans the full subscription set.
2. Incremental freshness stays within the 5-10 minute SLA under current load.
3. Full sync throughput remains bounded and does not materially degrade incremental freshness.
4. Operators can inspect pending, failed, and dead events directly from PostgreSQL.
5. Gap-triggered full sync requests are explainable from stored state and event history.
