---
title: Sync event append fails after commit during invalidation
status: fixed
severity: high
category: runtime
locations:
  - squirrel-backend/services/subscription_sync_event_service.py
  - squirrel-backend/services/sync_center_stream_service.py
source: manual
fixed_by: designs/des-fix-issue-006-sync-event-after-commit-invalidation.md
---

# Sync event append fails after commit during invalidation

## Phenomenon

The scheduled subscription outbox consumer fails while appending sync events after a subscription sync task is queued.

## Reproduction Evidence

Log excerpt:

```text
sqlalchemy.exc.InvalidRequestError: This session is in 'committed' state; no further SQL can be emitted within this transaction.
```

The traceback points to `append_event()` called by `SubscriptionScheduler._schedule_one_direct()`.

## Current Findings

- `SubscriptionSyncEventService.append_event()` registers after-commit invalidation callbacks.
- Those callbacks read `SYNC_CENTER_FEED_CHANNEL` and `SYNC_CENTER_RUN_CHANNEL` from the stream service instance.
- The default `SyncCenterStreamService` instance does not define those attributes; the constants exist at module level.
- Existing tests passed because they used a mock stream service with manually attached channel attributes.
- When a commit callback raises after the database commit, `get_session()` enters its exception path and tries to roll back an already committed transaction, masking the original callback failure.

## Impact

Outbox events can be consumed and task creation can complete in the database, but the sync event append path raises after commit. The consumer then marks the outbox event as failed, causing retry noise and potential duplicate scheduling attempts.

## Fix Attempts

- Updated `subscription_sync_event_service` to use module-level sync-center channel constants for after-commit invalidation callbacks.
- Added a regression test using a default-shaped stream service object without channel attributes.
- Verified the outbox consumer, scheduler, and sync-center stream tests.
