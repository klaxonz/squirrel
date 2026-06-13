---
title: Subscription and video service barrel modules hide real boundaries
status: open
severity: medium
category: architecture
locations:
  - squirrel-backend/services/subscription_service.py
  - squirrel-backend/services/video_service.py
source: audit
---

# Subscription and video service barrel modules hide real boundaries

## Phenomenon

`subscription_service.py` and `video_service.py` look like cohesive services but mainly re-export functions from CRUD, list, import, manage, and random modules.

## Current Findings

- Subscription call sites import `services.subscription_service` even when they only need one narrow read or write operation.
- Video call sites import `services.video_service` while the implementation is split across CRUD/list/random modules.

## Impact

The filenames suggest a single owner, but the actual behavior is spread across several modules. This makes write/read/manage boundaries harder to see.

## Fix Direction

Migrate call sites to explicit modules or replace the barrels with narrow, intentional facades.
