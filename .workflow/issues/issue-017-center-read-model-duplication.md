---
title: Center read-model services duplicate presentation helpers
status: open
severity: medium
category: architecture
locations:
  - squirrel-backend/services/subscription_sync_center_service.py
  - squirrel-backend/services/video_extraction_center_service.py
source: audit
---

# Center read-model services duplicate presentation helpers

## Phenomenon

Sync center and video extraction center services both implement site icon resolution, error summarization, and list item DTO shaping patterns.

## Current Findings

- Both services maintain site icon URL caches.
- Both services summarize errors into short UI-facing messages.
- Both services combine projection reads with presentation formatting.

## Impact

Presentation rules can drift between center views, and service classes keep growing with UI-facing helper logic.

## Fix Direction

Extract shared presentation policy only where the duplication is real, and keep projection readers separate from UI DTO formatting.
