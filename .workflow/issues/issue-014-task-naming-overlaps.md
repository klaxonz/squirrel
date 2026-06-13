---
title: Backend task naming overlaps across scheduler and crawl execution
status: open
severity: medium
category: architecture
locations:
  - squirrel-backend/schedule/task.py
  - squirrel-backend/services/scheduled_task_service.py
  - squirrel-backend/core/dynamic_task_manager.py
  - squirrel-backend/services/crawl_tasks/service.py
  - squirrel-backend/models/crawl_task.py
  - squirrel-backend/models/scheduled_task.py
source: audit
---

# Backend task naming overlaps across scheduler and crawl execution

## Phenomenon

The backend uses `task` for scheduler task definitions, scheduled task database configuration, dynamic task manager instances, and crawl execution tasks.

## Current Findings

- `schedule.task.BaseTask` represents scheduler task classes.
- `models.scheduled_task.ScheduledTask` stores scheduled job configuration.
- `models.crawl_task.CrawlTask` stores crawl execution work units.
- `core.dynamic_task_manager` manages scheduler task instances, not crawl tasks.

## Impact

Developers need context from imports to understand which kind of task a function handles.

## Fix Direction

Rename concepts over time toward explicit terms such as scheduler task definition, scheduled job config, and crawl task.
