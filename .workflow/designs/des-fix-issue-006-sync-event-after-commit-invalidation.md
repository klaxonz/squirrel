---
type: fix
name: issue-006
status: implemented
related_requirement:
related_issue: issues/issue-006-sync-event-after-commit-invalidation.md
---

# Fix Design: sync event after-commit invalidation failure

## Root Cause

The sync event service used module-level stream channel constants as if they were attributes on the stream service instance. Tests hid this by constructing a mock object with those attributes, while production uses the default instance without them.

## Fix Approach

1. Import the sync-center channel constants directly in `subscription_sync_event_service`.
2. Register after-commit invalidation callbacks with those module constants instead of instance attributes.
3. Add a focused test using the default-shaped stream service object without channel attributes so this cannot regress.

## Files

- `squirrel-backend/services/subscription_sync_event_service.py`: use direct channel constants for invalidation callbacks.
- `squirrel-backend/tests/services/test_sync_center_stream_service.py`: cover appending an event with a stream service that only exposes the publish method.

## Risks

The change affects only sync-center invalidation channel lookup. The published channel names remain the same.

## Similar Issues

Search found the same instance-channel lookup only in `subscription_sync_event_service.py`.

## Verification Results

Verification: lint Y  type-check SKIP  test Y  manual Y

- Lint: `pipenv run ruff check services/subscription_sync_event_service.py tests/services/test_sync_center_stream_service.py` passed.
- Test: `pipenv run pytest tests/services/test_sync_center_stream_service.py tests/services/test_outbox_event_service.py tests/services/test_subscription_update_scheduler.py` passed with `13 passed`.
- Manual: code trace confirms after-commit invalidation callbacks no longer read missing channel attributes from the stream service instance.
