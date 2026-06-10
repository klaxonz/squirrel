---
type: requirement
name: javdb-cloudflare-prewarm
status: implemented
---

# Requirement: javdb-cloudflare-prewarm

## Goal

Desktop app should warm up JavDB and MissAV Cloudflare bypass in the background so the first JavDB playback request does not spend the full Cloudflare solving time on the playback path.

## Scope

- Subproject: `squirrel-desktop`
- Sites: JavDB and MissAV document loading through the existing Camoufox Cloudflare document loader.
- Do not change backend playback fallback behavior.
- Do not change `site_runtimes/` Python files.

## Acceptance Criteria

1. After Electron app startup, JavDB and MissAV Cloudflare bypass start warming in the background without blocking window creation.
2. Prewarm uses the existing desktop document loading/Camoufox path and stores usable cookies/session state for later JavDB playback.
3. Prewarm failures are logged at debug level and do not break app startup or other provider prewarm tasks.
4. First JavDB playback still uses the existing provider path; no backend `/api/video/url` fallback is introduced.
5. The change has focused desktop-side test coverage for JavDB/MissAV prewarm registration and non-blocking failure behavior.

## Notes

- Current `squirrel-desktop/src/main.mjs` already calls `prewarmPlaybackProviders()` one second after app startup.
- Current provider prewarm registry only includes YouTube, so JavDB/MissAV can be added to that existing background prewarm mechanism.
- Current JavDB playback resolves the JavDB detail page first, then queries MissAV for the HLS stream, so both hosts need background prewarm.
