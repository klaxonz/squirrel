---
title: Scheduler tasks list is empty while statistics show tasks
status: fixed
severity: medium
category: runtime
locations:
  - squirrel-backend/routes/scheduler.py
source: manual
fixed_by: designs/des-fix-issue-008-scheduler-tasks-list-empty.md
---

# Scheduler tasks list is empty while statistics show tasks

## Phenomenon

The scheduled tasks page shows non-zero task statistics, but the task table is empty.

## Reproduction Evidence

The UI screenshot shows 10 total tasks and 5 active tasks, while the table renders the empty state.

## Current Findings

- `GET /api/scheduler/statistics` calls a static service method and can return statistics successfully.
- `GET /api/scheduler/tasks` calls `ScheduledTaskService.get_task_list(...)` on the class.
- `get_task_list()` is an instance method and requires `self`, so the route fails before returning the paginated task data.

## Impact

Users cannot view or operate scheduled tasks from the scheduler page even when tasks exist in the database.

## Fix Attempts

- Updated the tasks route to call `get_task_list()` on an injected `ScheduledTaskService` instance.
- Added a route regression test for `/api/scheduler/tasks`.
- Verified the route test, existing scheduled task service test, and ruff.
