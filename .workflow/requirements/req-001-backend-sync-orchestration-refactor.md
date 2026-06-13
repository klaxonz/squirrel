---
type: requirement
id: req-001
name: backend-sync-orchestration-refactor
status: in_progress
---

# Requirement: backend-sync-orchestration-refactor

## Goal

Refactor the backend subscription sync and video extraction orchestration so the async workflow has clearer ownership, fewer duplicate entry paths, and a single place to reason about sync state, crawl task creation, and progress events.

## Scope

- Subproject: `squirrel-backend`
- Primary modules:
  - `services/subscription_update/`
  - `services/crawl_tasks/`
  - `services/crawl_executors/`
  - `services/video_extraction/`
  - `services/video_extraction_projection_service.py`
  - `services/outbox_event_service.py`
  - `processes/managers/crawl_worker_runtime.py`
- Preserve existing HTTP API behavior for frontend and desktop callers.
- Preserve the Runtime V2 site plugin boundary.
- Do not modify `squirrel-backend/site_runtimes/` plugin runtime host internals unless the design proves it is directly required.
- Do not modify `squirrel-site-runtimes/` site plugin Python files.
- Do not introduce compatibility branches, fallback paths, or generic helper layers that do not remove real complexity.

## Acceptance Criteria

1. Subscription sync scheduling has one explicit public orchestration path for queued execution, and internal continuation paths do not call private scheduler methods from unrelated services.
2. Manual inline sync remains available if currently exposed by API, but its path shares the same state preparation and event semantics as queued sync instead of duplicating business rules.
3. Video extraction task creation is owned by a clearly named backend service boundary; `download_service` is no longer the conceptual owner for creating `video_extract` crawl tasks.
4. `subscription_sync_state.pending_video_count` changes are made through one clear coordination point, not scattered across strategy enqueue logic and extractor cleanup logic.
5. Crawl task lifecycle code remains responsible for task lease/status transitions, but does not own unrelated subscription progress or UI projection policy.
6. Sync center and extraction center projections continue to show queued, running, succeeded, and failed work accurately after the refactor.
7. Existing site runtime invocation behavior for `sync_subscription` and `extract_video` is preserved.
8. Existing frontend and desktop API contracts continue to pass their current backend route/service tests.
9. Relevant backend tests cover the refactored scheduling, outbox dispatch, video extraction enqueue, task completion, retry/failure, and projection update behavior.

## Notes

- Current architecture already has useful pieces: persistent `crawl_task`, dispatcher concurrency policy, worker lease renewal, Runtime V2 site plugins, and projection services.
- The refactor should keep those pieces and reduce cross-service coupling around subscription sync orchestration.
- The likely first design target is separating command/orchestration services from task lifecycle and projection update responsibilities.
