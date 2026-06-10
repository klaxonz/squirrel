---
title: Video extraction does not progress from subscription sync
status: fixed
severity: high
category: runtime
locations:
  - squirrel-backend/services/subscription_update/scheduler.py
  - squirrel-backend/services/subscription_sync_state_service/_crud.py
  - squirrel-backend/services/subscription_sync_state_service/_stale.py
  - squirrel-backend/processes/managers/scheduler_manager.py
source: manual
fixed_by: designs/des-fix-issue-004-video-extraction-not-working.md
---

# Video extraction does not progress from subscription sync

## Phenomenon

User reported that video collection/extraction appears unable to work normally.

## Current Findings

- `SubscriptionScheduler.schedule_one()` now writes `full_sync_due` / `incremental_sync_due` rows to `outbox_event` instead of creating `crawl_task` rows directly.
- The outbox event is converted into a real subscription sync crawl task only by the scheduler process outbox listener.
- `worker_process.py` starts queue workers and crawl workers, but does not start the outbox listener.
- `scheduler_manager.scheduler_start()` starts `outbox_event_service.run_notification_listener()`.
- `subscription_sync_state_service._crud.list_due_sync_states()` imports `_recover_stale_running_states_in_session` from `_recovery.py`, but the function is defined in `_stale.py`. This raises `ImportError` when due sync states are scanned.

## Reproduction Evidence

Command:

```bash
pipenv run pytest tests/services/test_outbox_event_service.py tests/services/test_subscription_update_scheduler.py tests/processes/test_scheduler_manager.py tests/processes/test_worker_manager.py
```

Observed result:

```text
4 failed, 8 passed
ImportError: cannot import name '_recover_stale_running_states_in_session' from 'services.subscription_sync_state_service._recovery'
```

## Impact

Scheduled due subscription sync can fail before emitting outbox events. Manual or scheduled sync requests that only publish outbox events will not reach crawl workers if the scheduler process or its outbox listener is not running.

## Fix Attempts

- Fixed the stale recovery import in `subscription_sync_state_service._crud`.
- Updated scheduler tests to bind outbox events to the test session and exercise the current database-backed sync-state lookup.
