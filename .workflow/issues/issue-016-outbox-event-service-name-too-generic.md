---
title: Outbox event service name is broader than supported behavior
status: open
severity: medium
category: architecture
locations:
  - squirrel-backend/services/outbox_event_service.py
source: audit
---

# Outbox event service name is broader than supported behavior

## Phenomenon

`OutboxEventService` is named like a generic event bus, but its event handler currently only supports `full_backfill_requested`.

## Current Findings

- Unsupported event types are skipped.
- The implemented handler is coupled to subscription full-backfill pressure and command dispatch.

## Impact

The generic name invites unrelated events to be added to the same service without a clear boundary.

## Fix Direction

Rename or narrow the service to subscription backfill outbox behavior, or introduce explicit event handlers by bounded context.
