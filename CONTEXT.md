# Squirrel

Squirrel tracks subscribed media sources, the videos discovered from them, and the user's local viewing and organization state.

## Language

**Subscription**:
A media source the user follows so Squirrel can discover and track its videos.
_Avoid_: Channel, feed, creator

**Subscription sync lifecycle**:
The lifecycle of a subscription refresh from request through queued, running, completed, skipped, failed, deferred, and recovered states.
_Avoid_: Scheduler, command flow, sync plumbing
