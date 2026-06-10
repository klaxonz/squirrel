---
type: fix
name: issue-004
status: implemented
related_requirement:
related_issue: issues/issue-004-video-extraction-not-working.md
---

# Fix Design: video extraction does not progress from subscription sync

## Root Cause

There are two likely failure points in the subscription-to-video-extraction path. First, `list_due_sync_states()` imports stale recovery logic from the wrong module, so due-state scheduling can fail with `ImportError`. Second, subscription scheduling is now outbox-first: `schedule_one()` only writes an outbox event, and only the scheduler process outbox listener converts that event into a crawl task. Running only the worker process is no longer enough for subscription sync to create video extraction work.

## Fix Approach

1. Correct the stale recovery import in `services/subscription_sync_state_service/_crud.py` to use the module where `_recover_stale_running_states_in_session` is actually defined.
2. Add or update focused tests around `list_due_sync_states()` so the import path is covered.
3. Verify the runtime contract for outbox consumption: scheduler process must be running, or the app must expose a deliberate startup path that starts the outbox listener. Do not add fallback direct task creation inside `schedule_one()`.

## Files

- `squirrel-backend/services/subscription_sync_state_service/_crud.py`: fix the stale recovery import.
- `squirrel-backend/tests/services/test_subscription_update_scheduler.py` or a focused sync-state test: cover due-state listing without import failure.
- Runtime docs or startup wiring may need an update if the intended deployment expects worker-only startup.

## Risks

- The import fix is low risk and local.
- Changing process startup wiring is higher risk because scheduler, outbox listener, and worker lifecycles are separate. It should be confirmed before implementation if the intended local startup path is ambiguous.

## Similar Issues

The same stale function is correctly re-exported from `services/subscription_sync_state_service/__init__.py` and defined in `_stale.py`, so the immediate import mismatch appears localized to `_crud.py`.

## Verification Results

Verification: lint Y  type-check SKIP  test Y  manual Y

- Lint: `pipenv run ruff check services/subscription_sync_state_service/_crud.py tests/services/test_subscription_update_scheduler.py` passed.
- Test: `pipenv run pytest tests/services/test_outbox_event_service.py tests/services/test_subscription_update_scheduler.py tests/processes/test_scheduler_manager.py tests/processes/test_worker_manager.py` passed with `12 passed`.
- Manual: code trace confirms `list_due_sync_states()` now imports the stale recovery helper from `_stale.py`, where it is defined. The outbox-first runtime contract remains unchanged: scheduler outbox listener converts sync due events to crawl tasks, and worker startup alone does not consume outbox events.
