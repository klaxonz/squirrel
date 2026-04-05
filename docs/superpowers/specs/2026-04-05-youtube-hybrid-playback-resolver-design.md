# YouTube Hybrid Playback Resolver Design

Date: 2026-04-05
Status: Proposed and user-approved for planning
Scope: `squirrel-backend`, `squirrel-plugins/youtube`

## Context

The current YouTube playback path is too slow for first play:

1. `/api/video/url` currently resolves YouTube playback through the plugin runtime on the hot path.
2. The existing YouTube plugin path is centered around `yt-dlp`, which is robust but heavy for online playback resolution.
3. Current YouTube site metadata disables `player_url_cache`, so repeated playback requests do not benefit from Redis-level playback caching.
4. The user requirement is not merely "play quickly"; the first successful response must provide the full playable source set rather than a single provisional stream.

Local feasibility validation was completed before this design:

1. `youtubei.js` was installed and tested in an isolated temporary directory.
2. With the `ANDROID` InnerTube client, the test video returned a complete `streamingData` set with direct stream URLs.
3. The same local validation showed that client selection matters: default web-style clients are not sufficient for this use case, while `ANDROID` is viable for public videos.

## Goals

1. Replace YouTube's default hot-path playback resolution with a lighter resolver based on `youtubei.js`.
2. Return a complete playback source set in the first successful response for supported public YouTube videos.
3. Preserve the existing backend API contract consumed by the frontend.
4. Keep `yt-dlp` as an explicit fallback for unsupported, restricted, or failed `youtubei.js` cases.
5. Add caching so repeated YouTube playback requests avoid full re-resolution.

## Non-Goals

1. Redesign frontend player APIs or the frontend playback source model.
2. Remove `yt-dlp` entirely from the codebase.
3. Solve every YouTube restricted-content case in the first iteration.
4. Generalize the new resolver architecture across all plugin sites in this same change.
5. Replace the existing MPD builder for non-YouTube sites.

## Recommendation

Implement a hybrid YouTube playback resolver:

- `youtubei.js` with the `ANDROID` InnerTube client becomes the primary resolver.
- `yt-dlp` remains the fallback resolver.
- The plugin keeps returning the same response shape: `video_url`, `audio_url`, `mpd_url`, and `qualities`.
- Redis-backed playback caching is enabled for YouTube and stores the final resolved playback payload.

This approach gives the best balance of playback latency, compatibility, and migration safety. It also respects the hard requirement that the first successful response should carry the full playback source set rather than a placeholder source.

## Alternatives Considered

### Alternative A: keep `yt-dlp` as the only resolver and only tune retries

Pros:

- Lowest implementation risk.
- No new runtime dependency.

Cons:

- Does not materially change the architecture that is causing slow first-play resolution.
- Still keeps a downloader-oriented stack on the hot path.

### Alternative B: fully replace `yt-dlp` with `youtubei.js`

Pros:

- Simplest steady-state architecture.
- Fastest main path if all target cases work.

Cons:

- Too risky for restricted, authenticated, and edge-format cases.
- Removes the current safety net before the new path has operational history.

### Alternative C: `youtubei.js` primary resolver with `yt-dlp` fallback

Pros:

- Optimizes the hot path while preserving compatibility coverage.
- Allows incremental hardening without frontend changes.
- Matches the user's performance goal and completeness requirement.

Cons:

- Introduces a dual-resolver maintenance surface.
- Requires a thin Node execution path for the `youtubei.js` worker.

Recommended choice: Alternative C.

## Target Behavior

### Supported public YouTube videos

- The plugin resolves playback through `youtubei.js` first.
- The primary resolver uses the `ANDROID` InnerTube client.
- The first successful response includes the full playable source set needed by the current frontend contract.
- The result is cached and reused for repeat requests.

### Restricted or unsupported cases

- If `youtubei.js` fails, returns incomplete stream data, or reports non-playable state, the plugin falls back to the current `yt-dlp` path.
- Fallback remains authoritative for authenticated, restricted, or otherwise incompatible cases in this phase.

### Response contract

The existing `VideoUrlDto` contract remains unchanged:

- `video_url`
- `audio_url`
- `mpd_url`
- `qualities`

The resolver internals may change, but the backend route and frontend consumer should not need a protocol migration.

## Architecture

### Backend entrypoint

`squirrel-backend/services/video_service.py` remains the single orchestration point for route-level playback resolution.

Responsibilities:

1. Keep the existing `get_video_url(video_id, force_refresh=False)` API.
2. Continue returning `VideoUrlDto`.
3. Enable Redis playback caching for YouTube by honoring updated site metadata.
4. Avoid any site-specific branching explosion in the backend service; YouTube-specific resolution strategy should remain inside the plugin.

### Plugin-level resolver structure

The YouTube plugin should be split into three logical layers.

#### 1. `youtubei_resolver`

Responsibilities:

1. Spawn or call a thin Node worker that uses `youtubei.js`.
2. Query YouTube through the `ANDROID` InnerTube client.
3. Return normalized streaming data for:
   - progressive formats
   - adaptive video formats
   - adaptive audio formats
   - quality metadata
   - playability status

This module is the primary source of truth for supported public-video playback resolution.

#### 2. `playback_mapper`

Responsibilities:

1. Convert normalized `youtubei.js` results into the current DTO semantics.
2. Decide how to populate:
   - `video_url`
   - `audio_url`
   - `mpd_url`
   - `qualities`
3. Preserve current frontend expectations without leaking raw `youtubei.js` objects.

#### 3. `yt_dlp_fallback`

Responsibilities:

1. Preserve the current `yt-dlp` playback path as a fallback-only implementation.
2. Reuse existing `handler.py`, `mpd.py`, and `ytdlp_support.py` behavior as much as possible.
3. Activate only when the primary resolver cannot produce an acceptable full result.

## Runtime Design

### Node worker

Introduce a thin Node worker under the YouTube plugin tree, for example:

- `squirrel-plugins/youtube/src/squirrel_youtube/node/youtubei_worker.mjs`

Responsibilities:

1. Accept a small JSON payload from Python.
2. Use `youtubei.js` to resolve playback metadata.
3. Prefer the `ANDROID` client.
4. Return a JSON payload containing normalized streaming data.

The worker must stay narrowly scoped. It is not a second application service; it is a helper runtime for one plugin capability.

### JavaScript evaluator support

Local testing showed that `youtubei.js` can resolve complete Android-client streaming URLs for public videos. It also showed that default Node execution still needs an explicit JavaScript evaluator hook when deciphering web-style formats.

For this design:

1. The primary path should prefer the `ANDROID` client because it returns direct URLs in the validated public-video case.
2. The worker should include a thin evaluator hook so the resolver remains robust if deciphering is required for a subset of returned formats.
3. This evaluator layer should stay local to the worker and must not leak complexity into Python plugin code.

## Caching Design

### Site metadata

Update YouTube site metadata in `config/sites.json`:

- `metadata.player_url_cache: true`

This enables Redis playback caching already supported by `video_service.py`.

### Cache payload

Cache the final playback response payload rather than a single URL.

The cached object should represent the complete playback result needed by `VideoUrlDto`, including:

- selected direct URLs
- optional MPD URL
- `qualities`

### Cache key shape

The cache key should at minimum distinguish:

1. `video_id`
2. resolver kind, such as `ytjs-android`
3. auth or cookie context when relevant

This avoids mixing anonymous and authenticated playback outcomes.

### Short-lived local cache

The Node worker may keep a small in-process cache for:

1. session/player metadata
2. recently resolved public-video streaming payloads

This local cache is an optimization layer, not the source of truth. Redis remains the cross-process cache.

## Fallback Rules

The plugin must fall back to `yt-dlp` when any of the following is true:

1. `youtubei.js` request fails.
2. `playabilityStatus` is not acceptable for playback.
3. The returned format set is incomplete for the current DTO contract.
4. The worker cannot produce a valid mapped playback payload.
5. The request is in a known restricted/authenticated scenario that the primary path does not yet support.

Fallback behavior should be explicit and observable in logs and metrics.

## Observability

Add stage-level timing and result logging for YouTube playback resolution.

Minimum stages:

1. cache lookup
2. `youtubei.js` worker invocation
3. result normalization and mapping
4. fallback activation
5. `yt-dlp` fallback duration
6. total `resolve_playback` duration

This is needed to verify that the architectural change actually improves the hot path.

## Validation Plan

### Functional validation

1. Public YouTube videos return a full playback source set from the primary resolver.
2. The current frontend can consume the response without protocol changes.
3. Known fallback scenarios still resolve through `yt-dlp`.

### Performance validation

1. First successful `/api/video/url` latency for public YouTube videos should materially improve relative to the current `yt-dlp`-first path.
2. Repeated playback requests should hit cache and avoid full re-resolution.

### Regression validation

1. Existing YouTube playback route tests continue to pass after response mapping changes.
2. New tests cover:
   - `youtubei.js` worker success mapping
   - fallback activation when primary data is incomplete
   - cache-key segregation
   - Redis cache hit behavior for YouTube playback

## Risks

1. YouTube may change client behavior for the `ANDROID` InnerTube path.
2. Public-video success does not guarantee parity for restricted or authenticated cases.
3. A Node worker adds a runtime dependency edge that must be packaged and supervised correctly.
4. URL lifetime and cache TTL must be tuned carefully to avoid replaying expired stream URLs.

## Open Implementation Constraints

These constraints are fixed for implementation:

1. The frontend playback contract must remain stable.
2. `yt-dlp` must remain available as fallback.
3. The primary resolver must target complete source-set resolution, not a single provisional stream.
4. The first implementation only needs to optimize YouTube; no cross-site abstraction rewrite is required.
