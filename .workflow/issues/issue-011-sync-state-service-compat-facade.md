---
title: Subscription sync state service exposes internals through compatibility facade
status: open
severity: high
category: architecture
locations:
  - squirrel-backend/services/subscription_sync_state_service/__init__.py
source: audit
---

# Subscription sync state service exposes internals through compatibility facade

## Phenomenon

`subscription_sync_state_service/__init__.py` re-exports many private functions and keeps module-level monkeypatch compatibility for tests.

## Current Findings

- The file starts with comments about backward compatibility for test monkeypatching.
- Internal modules such as `_crud`, `_events`, `_recovery`, `_stale`, and `_transitions` are re-exported from the package root.
- `SyncStateService` mostly delegates back to module-level functions instead of owning explicit dependencies.

## Impact

Production module structure is shaped by old test seams, and call sites can depend on internals that should remain private.

## Fix Direction

Expose a small sync-state public API and move dependency seams into explicit constructors or service instances.
