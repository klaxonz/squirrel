---
title: Subscription outbox consumer fails on missing site resolver
status: fixed
severity: high
category: runtime
locations:
  - squirrel-backend/services/subscription_update/scheduler.py
  - squirrel-backend/services/subscription_update/strategies/base.py
  - squirrel-backend/services/subscription_update/strategies/default_strategy.py
source: manual
fixed_by: designs/des-fix-issue-005-subscription-outbox-site-resolution.md
---

# Subscription outbox consumer fails on missing site resolver

## Phenomenon

The scheduled `SubscriptionSyncEventConsumerTask` fails while consuming a due subscription sync outbox event.

## Reproduction Evidence

Log excerpt:

```text
AttributeError: module 'services.subscription_sync_state_service' has no attribute '_resolve_site'
```

The failure occurs when `outbox_event_service` handles a `full_sync_due` event and calls `SubscriptionScheduler._schedule_one_direct()`.

## Current Findings

- `SubscriptionScheduler` calls `subscription_sync_state_service._resolve_site()` in `schedule_one()`, `run_one_inline()`, and `_schedule_one_direct()`.
- Subscription update strategies also call the same private attribute for event metadata and metrics.
- `subscription_sync_state_service` does not define or export `_resolve_site`.
- The project already has the direct URL site resolver in `utils.url_helper.resolve_site`.
- Existing tests monkeypatch `_resolve_site` with `create=True`, which hides the missing production attribute.

## Impact

Due sync outbox events can be claimed and then fail before creating the subscription sync crawl task. The event is retried instead of progressing the subscription sync pipeline.

## Fix Attempts

- Replaced subscription update calls to the missing `subscription_sync_state_service._resolve_site` attribute with direct `utils.url_helper.resolve_site` imports.
- Removed tests that created the missing `_resolve_site` attribute with `create=True`.
- Verified the outbox consumer path with focused service tests.
