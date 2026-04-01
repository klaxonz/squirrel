# Crawl Task Unification Design

**Status:** Approved

**Date:** 2026-04-01

**Goal:** Replace the current site-scoped Redis Stream topology with a unified crawl task model where the database is the source of truth, Redis is only a wakeup mechanism, and subscription sync plus video extraction run under one scheduler/runtime model.

**Non-Goals:**
- Do not redesign plugin extraction logic beyond the task boundary needed for the new executors.
- Do not remove existing sync history or trace/event concepts during the first rollout.
- Do not require a one-shot cutover from the current queue model.

---

## Problem

The current crawl subsystem scales infrastructure objects with site count instead of with workload shape.

Today:

- queue routing is site-aware at the Redis stream name level
- consumers are registered per `site x queue_type x mode`
- each consumer holds a long-lived blocking Redis read
- backpressure and pending-count reconciliation scan multiple site-specific streams
- subscription sync and video extraction share business flow but not one scheduling model

This creates four concrete problems:

- Redis connection usage grows roughly linearly with enabled site count.
- A new site requires queue topology growth rather than only plugin/runtime growth.
- Queue health, retries, and dead-letter behavior are fragmented across many streams.
- Crawl execution state is split between Redis streams, transient queue naming, and `subscription_sync_state`.

The architecture is encoding site differences too early in the pipeline. Site-specific behavior should exist in execution policy and plugin handlers, not in infrastructure topology.

---

## Chosen Approach

Use a database-backed crawl task system with a parent-child task model.

Core rules:

- The database is the only durable task source of truth.
- Redis no longer carries task semantics; it only nudges workers to check for runnable tasks.
- A subscription sync creates one parent job/task and may emit many child video extraction tasks.
- Workers claim tasks from the database using leases.
- Dispatcher logic enforces site fairness, site concurrency caps, task-type concurrency caps, retries, and stale-lease recovery.

This keeps queue object count stable while preserving site-aware execution.

---

## Target Model

### Parent Object: `crawl_job`

`crawl_job` represents one logical user-visible crawl run.

Typical usage:

- one manual or scheduled subscription sync creates one job
- that job owns one root `subscription_sync` task
- the root task may create many `video_extract` child tasks

Suggested fields:

- `id`
- `job_type`
- `source_type`
- `site`
- `subscription_id`
- `status`
- `priority`
- `trace_id`
- `payload`
- `created_at`
- `updated_at`
- `started_at`
- `finished_at`

Job status is an aggregate view for UI/history, not the scheduling primitive.

### Execution Object: `crawl_task`

`crawl_task` is the smallest schedulable unit.

Suggested fields:

- `id`
- `job_id`
- `parent_task_id`
- `task_type`
- `site`
- `subscription_id`
- `video_id`
- `video_url`
- `status`
- `priority`
- `payload`
- `dedupe_key`
- `attempt`
- `max_attempts`
- `next_run_at`
- `lease_until`
- `worker_id`
- `last_error`
- `last_error_type`
- `trace_id`
- `created_at`
- `updated_at`
- `started_at`
- `finished_at`

Recommended task types:

- `subscription_sync`
- `video_extract`

Recommended dedupe semantics:

- subscription sync: `subscription_sync:{subscription_id}:{mode}`
- video extract: `video_extract:{normalized_video_url}`

---

## Task State Machine

Use a small, explicit state machine.

Recommended states:

- `pending`
- `leased`
- `running`
- `retry_wait`
- `succeeded`
- `dead`
- `cancelled`

Flow:

1. Task is inserted as `pending`.
2. Dispatcher claims it atomically and sets `leased`, `worker_id`, `lease_until`.
3. Executor starts work and moves it to `running`.
4. Success moves it to `succeeded`.
5. Retriable failure moves it to `retry_wait` with a future `next_run_at`.
6. Exhausted retries move it to `dead`.
7. Stale leases are recovered back to `retry_wait` or `dead`.

Suggested defaults:

- `max_attempts = 3`
- lease TTL short enough to recover dead workers quickly
- exponential or stepped backoff for transient network/runtime errors
- immediate `dead` for deterministic errors such as unsupported site, missing subscription, or malformed payload

---

## Why Shared Scheduling Will Not Stall Small Sites

The worker model is not "single FIFO queue and hope for the best".

The dispatcher must enforce:

- per-site concurrency caps
- per-task-type concurrency caps
- site-aware fair selection
- optional site degradation/circuit breaking for unhealthy sites

That means:

- one slow site cannot consume all worker slots
- `video_extract` throughput cannot starve `subscription_sync`
- small, fast sites continue to run even when one large site is saturated

The fairness policy should be:

- choose only sites with runnable tasks and free site quota
- choose tasks inside a site by `priority`, then `next_run_at`, then `created_at`
- keep site selection round-robin or weighted-fair rather than global FIFO

---

## Dispatcher Responsibilities

The dispatcher owns scheduling policy.

Responsibilities:

- select runnable tasks from the database
- apply site-level concurrency control
- apply task-type concurrency control
- atomically lease tasks
- renew leases while tasks run
- recover expired leases
- classify failures into retriable vs terminal
- update job aggregate status

Redis wakeup is intentionally dumb. It should only reduce idle polling and should never be required to reconstruct task state.

---

## Executor Responsibilities

Executors own business execution only.

`subscription_sync` executor:

- load subscription context
- call the existing orchestrator/strategy layer or a thinner extracted equivalent
- persist sync progress into task/job records
- create child `video_extract` tasks instead of pushing directly to site queues

`video_extract` executor:

- parse the stored extract payload
- call the extraction pipeline
- mark child task success/failure
- update parent/job counters if needed

Executors must not decide global fairness or quota policy.

---

## Backpressure and Pending Counts

Current pending-count logic scans Redis streams to estimate queued extraction work.

The new model should stop scanning streams and instead query the database:

- count `video_extract` tasks for a subscription in `pending`, `leased`, `running`, or `retry_wait`
- use that count for subscription backpressure decisions
- expose site/task pending counts directly from database indexes

This removes expensive stream scans and makes counts correct even if Redis wakeup messages are lost or duplicated.

---

## Compatibility Strategy

The rollout should be phased.

Phase 1:

- add new job/task schema and core services
- keep old queue model active
- do not cut traffic yet

Phase 2:

- write new `video_extract` tasks while preserving existing behavior
- bring up the unified worker for extraction under a feature flag

Phase 3:

- route subscription sync scheduling into the new task model
- let sync tasks create extraction child tasks

Phase 4:

- turn off site-scoped queue routing
- retire per-site stream consumer registration
- downgrade Redis to wakeup-only or remove it from the crawl hot path

Feature flags should gate each phase.

---

## Existing Code Areas Affected

Primary code paths expected to change:

- `squirrel-backend/services/subscription_update/scheduler.py`
- `squirrel-backend/services/download_service.py`
- `squirrel-backend/services/subscription_sync_state_service.py`
- `squirrel-backend/services/video_extraction/*`
- `squirrel-backend/queues/direct_producer.py`
- `squirrel-backend/queues/consumer_registrar.py`
- `squirrel-backend/queues/runner.py`
- `squirrel-backend/consumer/processors/subscription_update_task.py`
- `squirrel-backend/consumer/processors/extract_task.py`
- `squirrel-backend/processes/managers/worker_manager.py`

New modules should be introduced instead of growing the current queue layer indefinitely.

---

## Risks

### Duplicate execution during migration

If old queue consumers and new DB workers are both active for the same logical task path, duplicate work can occur.

Mitigation:

- feature-flag every cutover
- use dedupe keys in the new task table
- migrate one execution path at a time

### Lease recovery bugs

Incorrect lease logic can cause stuck tasks or duplicate execution.

Mitigation:

- explicit tests for claim, renew, expire, and recover flows
- short lease duration with deterministic renewal

### Job status drift

If parent job aggregation is wrong, UI/history may regress.

Mitigation:

- keep aggregation rules simple
- test partial failure, success, and dead child scenarios

### Hidden queue-name coupling

Some code currently derives behavior from Redis stream names.

Mitigation:

- move behavior to explicit task fields
- keep compatibility adapters only temporarily

---

## Acceptance Criteria

- Crawl scheduling no longer requires one Redis consumer per site/mode/type.
- Database records are sufficient to reconstruct runnable, running, retriable, and dead crawl work.
- Subscription sync and video extraction use the same task store and lease model.
- One hot site cannot block unrelated sites from being scheduled.
- Subscription backpressure is computed from task records rather than Redis stream scans.
- Rollout can be phased safely behind feature flags.
