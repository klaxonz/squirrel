---
title: Video extraction code is split across core and service packages
status: open
severity: high
category: architecture
locations:
  - squirrel-backend/core/extraction
  - squirrel-backend/services/extraction
  - squirrel-backend/services/video_extraction
  - squirrel-backend/services/video_extraction_center_service.py
  - squirrel-backend/services/video_extraction_projection_service.py
source: audit
---

# Video extraction code is split across core and service packages

## Phenomenon

Video extraction engine, persistence, task enqueueing, progress recording, projection, and center read-model code live in several packages with overlapping names.

## Current Findings

- `core/extraction` contains pipeline and handler code.
- `services/extraction` contains persistence and actor/thumbnail processing services.
- `services/video_extraction` contains extraction orchestration, task enqueueing, and progress.
- Center and projection services remain as flat top-level service files.

## Impact

The boundary between extraction engine, persistence, task orchestration, and read-model presentation is unclear.

## Fix Direction

Move the video extraction bounded context behind one package with explicit engine, persistence, tasks, progress, and read-model modules.
