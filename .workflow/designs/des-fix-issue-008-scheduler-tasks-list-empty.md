---
type: fix
name: issue-008
status: implemented
related_requirement:
related_issue: issues/issue-008-scheduler-tasks-list-empty.md
---

# Fix Design: scheduler tasks list route calls service instance

## Root Cause

The scheduler route treated `ScheduledTaskService.get_task_list()` as a static method, while the service defines it as an instance method so tests can inject a session factory. Statistics still worked because `get_task_statistics()` is static, creating a split page state where counts load but list data does not.

## Fix Approach

1. Add a FastAPI dependency provider for `ScheduledTaskService`.
2. Call `get_task_list()` through the injected service instance in `/api/scheduler/tasks`.
3. Add a focused route test that requests `/api/scheduler/tasks` with a dependency override and asserts the paginated data is returned through the API envelope.

## Files

- `squirrel-backend/routes/scheduler.py`: call `get_task_list()` through a service instance.
- `squirrel-backend/tests/routes/test_scheduler_route.py`: cover the tasks route response shape.

## Risks

The change is limited to the scheduled task list endpoint. It does not alter filtering, pagination, database queries, or frontend response handling.

## Similar Issues

Search found `get_task_list()` used by this route and service tests only.

## Verification Results

Verification: lint Y  type-check SKIP  test Y  manual Y

- Lint: `pipenv run ruff check routes/scheduler.py tests/routes/test_scheduler_route.py tests/services/test_scheduled_task_service.py` passed.
- Test: `pipenv run pytest tests/routes/test_scheduler_route.py tests/services/test_scheduled_task_service.py` passed with `2 passed`.
- Manual: code trace confirms `/api/scheduler/tasks` now receives a `ScheduledTaskService` instance through FastAPI dependency injection before calling the instance method, matching the service test injection contract and returning the same paginated shape the frontend consumes.
