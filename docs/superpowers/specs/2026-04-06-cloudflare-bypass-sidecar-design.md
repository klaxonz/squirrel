# Cloudflare Bypass Sidecar Design

Date: 2026-04-06
Status: Proposed and user-approved for planning
Scope: `squirrel-backend`, `squirrel-cf-bypass`

## Context

The current Cloudflare bypass integration in `squirrel-backend` is only a thin HTTP client:

1. `squirrel-backend/utils/cloudflare_bypass.py` forwards `html` and `mirror` requests to `CLOUDFLARE_BYPASS_SERVICE_URL`.
2. Backend runtime wiring injects that client into shared runtime state and uses it from streaming proxy and connectivity fallback paths.
3. The actual bypass behavior lives outside this repository today.

That external dependency is undesirable for this project:

1. The code is harder to reason about and evolve because the critical behavior is not versioned with the main repository.
2. Operational ownership is blurred between the backend and an external implementation.
3. Existing backend integration is already narrow enough that importing a large generic scraper service would add unnecessary surface area.

The user-approved direction is:

1. Keep Cloudflare bypass as a separate process.
2. Keep the implementation code inside this repository.
3. Do not embed bypass internals into `squirrel-backend`.
4. Introduce a new repo-local subproject named `squirrel-cf-bypass`.

## Goals

1. Replace the current external Cloudflare bypass dependency with a repo-local sidecar service.
2. Preserve the current backend integration shape so migration risk stays low.
3. Support the current two required backend capabilities:
   - HTML retrieval after bypass
   - mirrored upstream requests after bypass
4. Keep cookie clearance caching and request-session reuse so the service does not need a browser per request.
5. Make the bypass implementation independently maintainable and deployable from the backend process.

## Non-Goals

1. Move bypass internals into the backend process.
2. Build a generic scraping platform or expose a large public API surface.
3. Introduce distributed cache, multi-node coordination, or advanced browser-pool orchestration in the first iteration.
4. Redesign existing plugin bypass call patterns.
5. Guarantee permanent Cloudflare compatibility across all protected sites.

## Recommendation

Create a new independent Python subproject named `squirrel-cf-bypass` that runs as its own ASGI service and implements only the minimum capabilities already required by the backend:

1. `GET /health`
2. `POST /cache/clear`
3. `GET /html?url=...`
4. mirrored upstream requests compatible with the current `x-hostname` based flow

This service should contain the heavy bypass internals:

1. browser-driven clearance solving
2. cookie and user-agent extraction
3. cookie cache
4. mirrored request execution with browser-like HTTP impersonation
5. request-session reuse

`squirrel-backend` should remain a client only. It continues to own runtime injection and fallback decisions, but not bypass mechanics.

## Alternatives Considered

### Alternative A: embed bypass internals directly into `squirrel-backend`

Pros:

1. One less process to run.
2. Fewer network hops between backend and bypass logic.

Cons:

1. Pollutes backend runtime with heavy browser dependencies.
2. Blurs service boundaries and makes backend packaging harder.
3. Increases maintenance risk because bypass behavior and backend APIs evolve at different rates.

This alternative was rejected because the user explicitly wants a separate process and a cleaner boundary.

### Alternative B: add a repo-local sidecar but only solve cookies, not request mirroring

Pros:

1. Smaller implementation surface.
2. Lower steady-state resource usage.

Cons:

1. Does not match the current backend interface shape.
2. Pushes more Cloudflare-sensitive request behavior back into the backend.
3. Weakens success rate for cross-host streaming and media paths that benefit from mirror mode.

This alternative was rejected because current usage already depends on both `html` and `mirror`.

### Alternative C: create a minimal repo-local sidecar with `html` and `mirror`

Pros:

1. Closest match to the current backend integration.
2. Lowest migration risk.
3. Keeps heavy bypass internals isolated from backend runtime.
4. Leaves room to evolve the solver implementation later without changing backend consumers.

Cons:

1. Still requires a separate service to supervise.
2. Still carries browser-level dependency weight.

Recommended choice: Alternative C.

## Architecture

### Repository structure

Add a new top-level subproject:

- `squirrel-cf-bypass/`

This subproject owns all bypass implementation details. `squirrel-backend` only depends on its HTTP API.

### Boundary with backend

`squirrel-backend` remains responsible for:

1. runtime client injection
2. deciding when bypass is needed
3. choosing `html` versus `mirror`
4. request fallback policy in backend-specific flows

`squirrel-cf-bypass` becomes responsible for:

1. browser startup and challenge solving
2. cookie and user-agent extraction
3. cache lifecycle
4. mirrored request execution
5. bypass-specific observability and health signaling

This preserves the existing architectural intent already visible in `squirrel-backend/utils/cloudflare_bypass.py`.

## Sidecar API

### `GET /health`

Purpose:

1. expose process health
2. confirm solver dependencies initialized correctly
3. report cache and session-pool summary

Minimum response should include:

1. service status
2. version string
3. browser-solver readiness
4. cache item count
5. session-pool item count

### `POST /cache/clear`

Purpose:

1. clear cached clearance data
2. clear reusable request sessions when needed for troubleshooting or forced refresh

This endpoint replaces the current external-service cache reset path. It should be explicit and operator-driven, not part of a frequent automatic purge loop.

### `GET /html`

Request:

1. `url` query parameter
2. optional control inputs such as proxy or cache bypass if needed later

Behavior:

1. restore cached clearance data when available
2. fall back to browser solving when cached state is missing or invalid
3. return final HTML content after bypass

Response headers should include:

1. final URL
2. user agent used for bypass
3. cookie count
4. processing time

### mirrored upstream requests

Behavior:

1. preserve the current `x-hostname` driven usage pattern
2. accept standard HTTP methods
3. merge incoming cookies with bypass cookies, giving clearance cookies priority
4. use impersonation-capable HTTP sessions for mirrored requests

Control headers:

1. `x-hostname` required
2. `x-proxy` optional
3. `x-bypass-cache` optional

The mirror endpoint shape should remain compatible with the current backend client expectation so existing call sites need minimal change.

## Internal Module Design

The new service should use a thin-server structure:

### `app/main.py`

Responsibilities:

1. create the FastAPI application
2. register routes
3. initialize shared services during startup
4. release resources during shutdown

### `app/api/routes.py`

Responsibilities:

1. define HTTP routes
2. validate inputs
3. translate internal results into HTTP responses

This layer should not contain bypass mechanics.

### `app/core/solver.py`

Responsibilities:

1. start browser context when needed
2. detect whether a challenge is present
3. solve the challenge
4. extract cookies, user agent, final URL, and HTML when required

This module should hide the concrete browser implementation behind a narrow interface so the solver can be replaced later without API churn.

### `app/core/cache.py`

Responsibilities:

1. store clearance cookies and associated user agent
2. expire stale entries
3. invalidate by host or by key
4. expose cache metrics to health reporting

The first version should use in-memory cache only. Persistent or distributed cache is unnecessary at this stage.

### `app/core/session_pool.py`

Responsibilities:

1. reuse impersonation HTTP sessions by host and proxy
2. bound session age and count
3. close expired sessions cleanly

### `app/core/mirror.py`

Responsibilities:

1. normalize and strip control headers
2. build the target URL
3. merge incoming cookies with clearance cookies
4. run mirrored upstream requests with session reuse
5. retry after forced cache invalidation when an upstream block indicates stale clearance

### `app/core/models.py`

Responsibilities:

1. internal dataclasses or pydantic models
2. normalized solver result structures
3. cache record structures
4. health response models

### `app/core/settings.py`

Responsibilities:

1. centralize environment configuration
2. define sane defaults
3. avoid ad hoc env parsing across modules

## Runtime Design

### Process model

`squirrel-cf-bypass` runs as a standalone ASGI service. It should be independently startable in development and production.

The service keeps three categories of runtime state:

1. solver resources
2. clearance cache
3. mirrored-request session pool

### Solver behavior

The solver should only run when cache cannot satisfy the request or when bypass is explicitly forced.

Successful solver output should include:

1. cookie map
2. user agent
3. final URL
4. optional HTML content for the `/html` path

### Cache strategy

The cache key should at minimum distinguish:

1. hostname
2. proxy identity when present

Each entry should include:

1. cookies
2. user agent
3. created timestamp
4. expiration timestamp

The first version should be conservative and invalidate cache on explicit operator action or on strong evidence of stale clearance such as repeated block responses after mirror reuse.

### Session reuse

Mirrored requests should reuse impersonation-capable HTTP sessions by host and proxy. This reduces repeated handshake cost and keeps request behavior more stable than per-request session creation.

## Technology Choices

Recommended first-version stack:

1. `FastAPI` for the service API
2. `uvicorn` for serving
3. `curl_cffi.requests.AsyncSession` for mirrored request impersonation
4. a browser-based solver module behind a local abstraction

The browser solver implementation may use Camoufox- or Playwright-based logic internally, but those details must stay inside the solver module and not leak into the backend contract.

## Backend Migration Plan

### Backend compatibility target

The backend should keep using `CLOUDFLARE_BYPASS_SERVICE_URL` as its configuration surface in the first migration phase. That keeps the backend client stable while switching the target service implementation.

### Expected backend changes

Keep backend changes minimal:

1. point `CLOUDFLARE_BYPASS_SERVICE_URL` at the new repo-local sidecar
2. keep `CloudflareMirrorClient` behavior compatible with the new sidecar API
3. avoid moving bypass logic into backend modules

Current consumers that should continue to work with the new sidecar:

1. streaming proxy bypass flow
2. connectivity fallback flow
3. plugin flows that rely on `bypass_mode='html'` or `bypass_mode='mirror'`

### Heartbeat behavior

The current cache-clear heartbeat pattern should not remain the default behavior for the new sidecar.

Reason:

1. frequent forced cache clearing defeats the value of clearance caching
2. it increases browser churn and resource cost
3. it makes bypass performance less predictable

The current periodic cache clear should be removed or replaced with health verification rather than routine cache invalidation.

## Configuration

Recommended sidecar settings:

1. `CF_BYPASS_HOST`
2. `CF_BYPASS_PORT`
3. `CF_BYPASS_LOG_LEVEL`
4. `CF_BYPASS_CACHE_TTL_SECONDS`
5. `CF_BYPASS_SESSION_TTL_SECONDS`
6. `CF_BYPASS_MAX_CONCURRENT_BROWSERS`
7. `CF_BYPASS_REQUEST_TIMEOUT_SECONDS`
8. `CF_BYPASS_HEADLESS`
9. `CF_BYPASS_PROXY_URL`

Backend keeps:

1. `CLOUDFLARE_BYPASS_SERVICE_URL`

This split keeps backend configuration stable while allowing the sidecar to evolve independently.

## First-Version Scope

The first version should include:

1. standalone `squirrel-cf-bypass` subproject
2. health endpoint
3. cache clear endpoint
4. HTML retrieval endpoint
5. mirrored request handling
6. in-memory clearance cache
7. reusable impersonation sessions
8. basic logging and timing visibility

The first version should not include:

1. distributed or persistent cache
2. multi-backend solver plugins
3. complex browser pool scheduling
4. generalized scraping workflows
5. broad backend API redesign

## Observability

Minimum logging and metrics coverage should include:

1. solver invocation start and end
2. cache hit versus cache miss
3. mirror request duration
4. forced cache invalidation on block
5. endpoint processing duration
6. health summary counts for cache and session reuse

Logs should make it possible to distinguish:

1. solver failure
2. cache miss
3. stale cookie reuse
4. mirrored request block
5. upstream timeout

## Validation Plan

### Functional validation

1. backend `html` bypass callers work against the new sidecar without protocol redesign
2. backend `mirror` bypass callers work against the new sidecar without protocol redesign
3. current JavDB-related bypass paths continue to function with the new implementation

### Migration validation

1. swapping only `CLOUDFLARE_BYPASS_SERVICE_URL` is sufficient for first-phase backend integration
2. backend runtime injection remains unchanged in shape
3. no bypass internals are moved into backend code

### Runtime validation

1. repeated requests reuse cached clearance where valid
2. repeated mirror requests reuse sessions where valid
3. explicit cache clear forces fresh solver behavior on the next protected request

## Risks

1. Cloudflare challenge behavior can change and may reduce solver effectiveness over time.
2. Browser-backed solving remains resource-intensive even when isolated in a sidecar.
3. Some sites may still require high-quality proxy or IP rotation support beyond what the first version provides.
4. Media and cross-host requests can still fail even when initial clearance succeeds.
5. An overly aggressive cache TTL can cause stale-clearance failures, while an overly short TTL can cause avoidable browser churn.

## Fixed Implementation Constraints

These constraints are part of the approved design:

1. bypass logic stays in a separate process
2. implementation code lives in this repository
3. the new process is a distinct subproject named `squirrel-cf-bypass`
4. `squirrel-backend` remains a client, not the bypass implementation host
5. first-version scope is intentionally narrow and should serve only current project needs
