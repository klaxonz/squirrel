---
title: Subscription sync center service has too many responsibilities
status: open
severity: high
category: architecture
locations:
  - squirrel-backend/services/subscription_sync_center_service.py
source: audit
---

# Subscription sync center service has too many responsibilities

## Phenomenon

`SubscriptionSyncCenterService` combines dashboard aggregation, query orchestration, DTO serialization, queue rank lookup, site icon resolution, recent-run cache, and error summarization.

## Current Findings

- Site icon resolution and cache live inside the dashboard service.
- Queue-rank lookup reaches into crawl task state.
- Feed recent-run serialization and dashboard query assembly are implemented in the same class.

## Impact

Small sync-center behavior changes require touching a large service that mixes presentation, read-model, and task-state concerns.

## Fix Direction

Split the service into dashboard orchestration, item/run serialization, site icon resolution, and queue rank reading modules.
