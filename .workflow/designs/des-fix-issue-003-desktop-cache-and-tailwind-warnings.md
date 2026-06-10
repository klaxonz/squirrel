---
type: fix
name: issue-003
status: implemented
related_requirement:
related_issue: issues/issue-003-desktop-cache-and-tailwind-warnings.md
---

# Fix Design: desktop cache and Tailwind warnings clutter dev output

## Root Cause

The trigger is normal JavDB playback, not the dev-server restart. The frontend playback page calls the desktop bridge with `forceRefresh: false`; the Electron IPC handler forwards that into `resolveJavdbPlayback()`, which checks the shared adult playback cache before loading pages. The first playback for a normalized JavDB URL has no matching hashed JSON file in `%USERPROFILE%\.squirrel\playback-cache`, so `readFile()` raises `ENOENT`. The file-cache loader treats that normal cache miss like a debug-worthy load error and prints a stack trace.

The spotlight hero separately uses `duration-[10000ms]`, which Tailwind reports as ambiguous because the same arbitrary value syntax can match multiple duration utilities.

## Fix Approach

Return `null` without logging when `readFile` reports `ENOENT`, while keeping debug logging for corrupted cache entries or other read failures. Replace the ambiguous Tailwind class with an explicit arbitrary CSS property for transition duration.

## Files

- `squirrel-desktop/src/shared/file-cache.mjs`: handle missing cache files as normal misses.
- `squirrel-desktop/tests/file-cache.test.mjs`: cover missing cache files without debug logging.
- `squirrel-desktop/tests/javdb-provider.test.mjs`: cover the normal non-force-refresh JavDB playback path on a cold cache.
- `squirrel-frontend/src/views/LatestVideos.vue`: use explicit `[transition-duration:10000ms]` classes.

## Risks

Low. Existing cache hit, cache expiry, and cache save behavior stay unchanged. The frontend animation duration remains the same.

## Similar Issues

`rg` found `duration-[10000ms]` only in `LatestVideos.vue`. `loadFileCache` is the shared disk-cache read path, so the cache-miss logging issue is fixed at the source.

## Verification Results

Verification: lint SKIP  type-check Y  test Y  manual Y

- Lint: skipped; neither touched subproject defines a dedicated lint script.
- Type-check: `npm run build:check` in `squirrel-frontend` passed.
- Test: `node --test tests/file-cache.test.mjs tests/javdb-provider.test.mjs` in `squirrel-desktop` passed.
- Manual: `npm run build:check` completed without the previous `duration-[10000ms]` warning, and the focused file-cache test confirmed a missing cache file returns `null` without `console.debug`.
