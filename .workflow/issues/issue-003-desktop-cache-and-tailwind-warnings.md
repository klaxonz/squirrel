---
title: Desktop cache and Tailwind warnings clutter dev output
status: fixed
severity: medium
category: runtime
locations:
  - squirrel-desktop/src/shared/file-cache.mjs
  - squirrel-desktop/tests/file-cache.test.mjs
  - squirrel-frontend/src/views/LatestVideos.vue
source: manual
fixed_by: designs/des-fix-issue-003-desktop-cache-and-tailwind-warnings.md
---

# Desktop cache and Tailwind warnings clutter dev output

## Phenomenon

Development output shows a Tailwind ambiguity warning for `duration-[10000ms]` and logs a desktop file-cache `ENOENT` stack trace when a playback cache file does not exist.

## Impact

Expected cache misses look like runtime failures, and the Tailwind warning adds noise to frontend build/dev output.

## Reproduction

Run the desktop/frontend development flow and open a JAVDB playback URL through the normal video playback page. The normal playback path uses `forceRefresh: false`, so `resolveJavdbPlayback()` checks the disk playback cache before loading the JavDB/MissAV pages. On first playback for that normalized URL, the hashed cache file under `%USERPROFILE%\.squirrel\playback-cache` does not exist and `readFile()` raises `ENOENT`.

## Fix Attempts

- Handled missing disk cache files as normal cache misses without debug logging.
- Replaced ambiguous Tailwind duration classes with explicit transition-duration arbitrary properties.
