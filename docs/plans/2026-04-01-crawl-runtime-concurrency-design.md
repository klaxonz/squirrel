# Crawl Runtime Concurrency Design

**Date:** 2026-04-01

## Goal

Replace the current "one worker loop executes one task at a time" crawl runtime with a small number of worker processes that each own multiple in-process execution slots, while keeping site and task-type quotas correct across processes.

## Problem

The current runtime couples total crawl throughput to the number of worker loops. One loop can execute only one task at a time, so higher throughput requires many worker threads or processes. The previous dispatcher also enforced quotas with a snapshot-then-claim flow, which is not safe once multiple processes claim tasks concurrently.

## Runtime Model

- Deployment controls process count.
- Each worker process runs one crawl runtime coordinator thread.
- The runtime coordinator owns a fixed-size thread pool.
- Each pool thread executes one claimed crawl task.
- Total concurrency is `process_count * slots_per_process`.

This keeps process count low while allowing high task concurrency.

## Cross-Process Quota Enforcement

The dispatcher must stop using best-effort snapshots for quota enforcement.

The new design introduces dispatch scope rows:

- `scope_type = site`, `scope_key = <site>`
- `scope_type = task_type`, `scope_key = <task_type>`

These rows are used as lock namespaces, not as counters.

Atomic claim flow:

1. Select runnable task candidates in priority order.
2. Lock the candidate task row with `FOR UPDATE SKIP LOCKED`.
3. Lock the matching site scope row.
4. Lock the matching task-type scope row.
5. Count current `leased/running` tasks for that site and task type inside the same transaction.
6. If both quotas allow execution, mark the task as `leased` and return it.

Because claims for the same site or task type serialize on shared scope rows, quota checks remain correct across processes without requiring one process per site.

## Scope Row Lifecycle

- Migration backfills scope rows from existing crawl tasks.
- New task creation ensures both site and task-type scope rows exist.
- Claim logic still lazily creates missing rows as a safety net for tests or legacy data.

## Runtime Execution Flow

1. Reap completed futures.
2. Recover expired tasks.
3. Fill available execution slots by repeatedly claiming runnable tasks.
4. Submit each claimed task to the local thread pool.
5. Worker thread starts, executes, and completes or retries the task.
6. Coordinator sleeps only when there are no free slots or no runnable tasks.

## Config

- Keep deployment-level process count external.
- Add `CRAWL_SLOTS_PER_PROCESS` for in-process execution capacity.
- Keep `CRAWL_TASK_TYPE_LIMITS` and site concurrency overrides as shared quota policy inputs.

## Tests

- Runtime test: one process can execute multiple tasks concurrently via slots.
- Dispatcher test: quota enforcement still skips blocked sites/task types.
- Atomic claim test: sequential claims respect quotas under locked scope rows.
- Manager test: crawl worker manager starts one runtime coordinator, not one thread per slot.
