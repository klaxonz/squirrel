# Sync Center SSE Cookie Auth Design

Date: 2026-04-05
Status: Proposed and user-approved for planning
Scope: `squirrel-backend`, `squirrel-frontend`

## Context

The current `SyncCenter` page is not actually real-time from the browser's perspective:

- Backend sync-state and extraction projections are updated immediately when domain events or task state changes occur.
- Frontend still reads those projections through periodic HTTP polling.
- The current page-level refresh interval is `15000ms`.

The repository also uses a JWT model centered on frontend-managed bearer tokens:

- Login stores the access token in `localStorage`.
- Axios injects `Authorization: Bearer ...` on each request.
- Backend route protection is built around `OAuth2PasswordBearer`.

This token model blocks direct adoption of browser-native `EventSource`, because native SSE connections cannot attach custom authorization headers.

## Goals

1. Make the `SyncCenter` page update in near real-time without polling.
2. Use browser-native `EventSource` rather than a custom streaming client.
3. Replace frontend-managed bearer-token auth with `HttpOnly` cookie auth in one cut.
4. Keep the existing sync and projection models intact.
5. Reuse existing snapshot-building services instead of inventing a second realtime data model.

## Non-Goals

1. Introduce WebSocket infrastructure.
2. Keep backward compatibility with `localStorage` tokens or bearer-header auth.
3. Rework sync-center projection schemas.
4. Realtime-enable unrelated pages in the same change.
5. Preserve the current 15-second polling path as a fallback.

## Recommendation

Adopt a clean one-time migration to cookie-based auth plus SSE-driven sync-center updates:

- Backend login writes an `HttpOnly` auth cookie.
- Backend protected routes authenticate from that cookie.
- Frontend removes token storage and bearer-header injection entirely.
- `SyncCenter` opens one SSE connection and receives complete snapshot events.

This keeps the transport simple, keeps auth aligned with native browser behavior, and avoids carrying two authentication systems or two refresh strategies at once.

## Alternatives Considered

### Alternative A: reduce polling interval

Pros:

- Lowest implementation effort.
- Minimal structural change.

Cons:

- Still not realtime.
- Generates continuous background load.
- Leaves auth and transport limitations unresolved.

### Alternative B: fetch-based SSE with bearer headers

Pros:

- Avoids auth migration.
- Works with the current token model.

Cons:

- Does not use native `EventSource`.
- Requires custom stream parsing and reconnect behavior.
- Preserves the existing token architecture the user wants removed.

### Alternative C: native SSE plus `HttpOnly` cookie auth

Pros:

- Matches native browser SSE behavior.
- Removes token handling from frontend JavaScript.
- Produces a simpler end-state architecture.

Cons:

- Requires coordinated frontend and backend release.
- Forces a full auth migration in one change.

Recommended choice: Alternative C.

## Target Architecture

### Authentication model

The system will move from frontend-owned JWT storage to server-issued cookie auth.

- Login success writes a secure auth cookie via `Set-Cookie`.
- The cookie must be `HttpOnly`.
- The cookie must also be `Secure` and `SameSite=Lax`.
- The frontend will no longer store access tokens in `localStorage`.
- Protected API routes will authenticate from the cookie rather than from `Authorization` headers.
- Existing bearer-based route protection will be removed rather than preserved.

This is a hard cut. Old clients that still rely on bearer headers are expected to stop working after release.

This design assumes the frontend and backend remain same-origin for authenticated browser traffic. Supporting cross-site frontend deployment is out of scope for this change.

### Sync center realtime model

The `SyncCenter` page will use one `EventSource` connection:

- Endpoint: `GET /api/subscription/sync-center/stream`
- Query parameter: `selectedRunId` optional

The connection is page-scoped and serves both tabs:

- feed sync dashboard
- extraction dashboard
- selected run detail, when present

The page will no longer use the 15-second polling timer after this migration.

## SSE Event Model

### Event strategy

Use full snapshot events, not field-level patch events.

Each push replaces one logical slice of page state:

- `feed_snapshot`
- `extract_snapshot`
- `run_detail`
- `heartbeat`

This keeps frontend state handling simple and reuses the current backend snapshot assembly logic.

### Initial connection behavior

When a client connects, the server immediately emits:

1. `feed_snapshot`
2. `extract_snapshot`
3. `run_detail` when `selectedRunId` is provided

This ensures first paint and later updates use the same event contract.

### Update behavior

When a relevant backend change occurs:

- recompute the affected snapshot
- emit a fresh full event payload for that slice

No frontend merge logic is required beyond replacing the corresponding state block.

## Backend Design

### Auth changes

Backend auth must be refactored to treat cookie auth as the only supported mechanism.

Required changes:

- Login route sets the auth cookie.
- Logout clears the auth cookie.
- `get_current_user` and related helpers read the token from the cookie.
- Protected routes stop depending on the bearer-only FastAPI security flow.

### SSE route

Add a sync-center stream route under the existing subscription routes.

Responsibilities:

- authenticate the current user from cookie auth
- open a long-lived `text/event-stream` response
- emit initial snapshots
- subscribe to sync-center invalidation notifications
- emit updated snapshots as relevant changes occur
- emit heartbeat frames periodically to keep intermediaries from closing the connection

### Realtime invalidation channels

Reuse Redis pub/sub as the invalidation transport.

Add channels for sync-center updates, for example:

- `squirrel:sync-center:feed`
- `squirrel:sync-center:extract`
- `squirrel:sync-center:run`

Publishing rules:

- feed sync event/projection changes publish feed invalidation
- extraction projection refresh publishes extract invalidation
- run-detail event changes publish run invalidation with `run_id`

The SSE route listens for these notifications and decides whether to recompute and emit the relevant snapshot for the connected user.

### Snapshot producers

Do not create a parallel realtime-only formatter.

Reuse and extend existing services:

- `subscription_sync_center_service.get_feed_dashboard_snapshot`
- extraction center snapshot assembly based on the current overview and preview queries
- sync run detail and event queries already used by the run-detail drawer

If needed, add explicit helper functions for extraction snapshot and run-detail snapshot so both HTTP and SSE can share the same assembly code.

## Frontend Design

### Auth migration

Frontend auth becomes cookie-first and cookie-only.

Required removals:

- `localStorage` token persistence
- axios bearer-header injection
- token-based login-state bootstrap

Required behavior:

- login succeeds based on normal API success and cookie issuance
- current-user bootstrap relies on authenticated `/me` style requests
- logout clears local user state and calls the backend logout endpoint that clears the cookie

### Sync center data flow

`SyncCenter.vue` becomes event-driven.

Responsibilities:

- create one `EventSource` for the page
- pass `selectedRunId` in the stream URL when a run drawer is open
- replace feed state on `feed_snapshot`
- replace extraction state on `extract_snapshot`
- replace selected run detail state on `run_detail`
- rebuild the SSE connection when `selectedRunId` changes

The page no longer owns a polling timer after the migration.

### Error behavior

- If the SSE request is rejected with `401`, redirect to login.
- If the connection drops, rely on native `EventSource` reconnect behavior.
- The page does not retain the old polling fallback.

This is intentional. The system should have one refresh strategy, not two competing ones.

## Deployment Boundary

This work requires a coordinated frontend and backend release.

Implications:

- The old frontend will not be compatible with the new backend auth model.
- Users should expect to log in again after deployment.
- Frontend and backend must be released together.

This migration should be treated as a single feature cut, not as an incremental compatibility rollout.

## Risks

1. Cookie auth migration can break every protected route if the auth helper conversion is incomplete.
2. SSE connections can be dropped by intermediaries if heartbeat behavior is missing or too sparse.
3. Recomputing full snapshots too often can create avoidable DB load if invalidation events are too noisy.
4. A run-detail stream bound to `selectedRunId` requires careful reconnect behavior when the drawer target changes.
5. Removing polling means realtime correctness depends entirely on SSE and invalidation reliability.
6. Cookie auth introduces CSRF exposure if cookie attributes and deployment assumptions are left implicit.

## Mitigations

1. Convert auth centrally first, then update route usage consistently.
2. Add heartbeat events and verify the route stays open behind the current deployment path.
3. Publish invalidations only after real projection changes, not on every internal step that does not affect snapshots.
4. Keep the event contract coarse-grained and deterministic: full snapshot replacement only.
5. Add route-level and page-level tests that prove realtime updates actually land without polling.
6. Require same-origin deployment for this cut and set the auth cookie with `Secure` and `SameSite=Lax`.

## Verification Plan

### Backend verification

1. Login returns success and sets the auth cookie.
2. Protected routes succeed with cookie auth and fail without it.
3. SSE stream rejects unauthenticated requests with `401`.
4. Feed projection changes emit `feed_snapshot`.
5. Extraction projection changes emit `extract_snapshot`.
6. Run event changes emit `run_detail` for subscribed `selectedRunId`.

### Frontend verification

1. Login no longer writes tokens to `localStorage`.
2. Authenticated requests still succeed through cookie auth.
3. `SyncCenter` opens one `EventSource` connection on mount.
4. Feed tab updates immediately after a sync-state change.
5. Extract tab updates immediately after extraction task changes.
6. Opening a run drawer and receiving a new event updates the drawer without waiting for a poll cycle.

### Manual integration verification

1. Log in with the new auth flow.
2. Open `SyncCenter`.
3. Trigger a manual subscription refresh.
4. Confirm feed board state changes without waiting 15 seconds.
5. Confirm extraction progress updates while extraction tasks move through queued/running/completed states.
6. Open a run detail drawer and confirm new events appear live.

## Implementation Notes For Planning

Implementation should be sequenced in this order:

1. backend cookie auth conversion
2. backend SSE route and invalidation publishing
3. frontend auth cleanup
4. frontend sync-center SSE consumption
5. verification and cleanup

That ordering reduces ambiguity during the auth cut and keeps the realtime page work on top of the final auth model rather than on a transitional one.
