---
title: Backend contains unused modules left after earlier refactors
status: fixed
severity: medium
category: maintainability
locations:
  - squirrel-backend/services/music
  - squirrel-backend/sql/video_sql.py
  - squirrel-backend/core/repository
  - squirrel-backend/queues/duplicate_checker.py
source: audit
---

# Backend contains unused modules left after earlier refactors

## Phenomenon

Some backend modules have no internal call sites and are not runtime entry points.

## Reproduction Evidence

Static import and `rg` reference checks found only self-references or package exports for the affected modules.

## Current Findings

- The actual music route imports `services.music.MusicService`; the split music modules are not imported by the route, service root, or tests.
- `sql/video_sql.py` is not used by video listing code.
- `core.repository.BaseRepository` has no subclasses or imports.
- Queue duplicate checker exports are not used by producers, consumers, worker processes, or tests.

## Impact

Unused modules make the backend look larger and more layered than it is, and they create false architecture signals for future refactors.

## Fix Attempts

- Removed unused split music modules; the active implementation remains in `services.music`.
- Removed unused raw video SQL helpers and package export.
- Removed unused repository base package.
- Removed unused queue duplicate checker and package exports.
- Verified no remaining repository references with `rg`.
- Verified lint and focused tests.
