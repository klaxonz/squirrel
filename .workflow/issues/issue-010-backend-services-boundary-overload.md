---
title: Backend services package mixes multiple architectural layers
status: open
severity: high
category: architecture
locations:
  - squirrel-backend/services
source: audit
---

# Backend services package mixes multiple architectural layers

## Phenomenon

The backend `services` package contains domain services, infrastructure services, read-model aggregators, task orchestration, site runtime access, RSS/music clients, and projection maintenance in one flat namespace.

## Current Findings

- Feature modules such as subscription, video, RSS, music, sync center, crawl task, and site runtime all share the same top-level package.
- Some domains have subpackages, while related files for the same domain still remain flat beside unrelated services.
- This makes module ownership unclear and encourages facade modules that hide actual read/write/orchestration boundaries.

## Impact

New backend changes need more global search to find the right owner, and refactors tend to add new files beside existing ones instead of improving domain boundaries.

## Fix Direction

Group code by bounded context and keep only explicit public entry points per context.
