---
type: feature
name: javdb-cloudflare-prewarm
status: implemented
related_requirement: requirements/req-javdb-cloudflare-prewarm.md
related_issue:
---

# Feature Design: javdb-cloudflare-prewarm

## Requirement Mapping

| Acceptance Criteria | Implementation |
| --- | --- |
| Startup starts JavDB and MissAV prewarm without blocking window creation | Reuse the existing `prewarmPlaybackProviders()` call scheduled by `main.mjs` after window creation. |
| Prewarm uses existing Camoufox document loading path | Register a JavDB provider prewarm task that calls `loadDocumentHtmlWithBrowserWindow()` for `https://javdb.com/` and `https://missav.ai/`. |
| Prewarm failures do not break startup or other provider tasks | Catch and debug-log each host-level failure inside the JavDB prewarm task; keep provider registry catch as the outer safety net. |
| First JavDB playback keeps the existing provider path | Only add background prewarm; do not change `resolveJavdbPlayback()` routing or add backend `/api/video/url` fallback. |
| Focused desktop-side test coverage | Add Node tests for exported JavDB/MissAV prewarm behavior and provider registry registration. |

## Files

- `squirrel-desktop/src/playback/providers/javdb/index.mjs`: export `prewarmJavdbCloudflare()` that warms both required hosts through an injected document loader.
- `squirrel-desktop/src/playback/providers/index.mjs`: register the JavDB prewarm task beside YouTube and pass the existing desktop document loader.
- `squirrel-desktop/tests/javdb-provider.test.mjs`: cover target URLs, document loader options, and failure swallowing.
- `squirrel-desktop/tests/playback-prewarm.test.mjs`: assert JavDB prewarm registration.

## Reuse Check

- Reuse `main.mjs` startup scheduling; no new app lifecycle hook.
- Reuse `loadDocumentHtmlWithBrowserWindow()` so cookies/session state flow through the existing Camoufox loader.
- Reuse the provider registry pattern already used by YouTube.

## Risks

- Startup may consume background resources while Camoufox solves Cloudflare. The existing one-second deferred provider prewarm keeps this off the window creation path.
- Cloudflare challenge behavior can vary. Host-level failures are logged and do not alter playback behavior.

## Implementation Order

1. Add JavDB/MissAV prewarm export to the JavDB provider.
2. Register it in the desktop provider prewarm registry.
3. Add focused tests.
4. Run desktop Node tests for touched behavior.

## Verification Results

Verification: lint SKIP  type-check SKIP  test Y  manual Y

- Test: `node --test tests/javdb-provider.test.mjs` passed with 8 tests.
- Test: `node --test tests/playback-prewarm.test.mjs` passed with 1 test.
- Manual: code trace confirms `main.mjs` still starts `prewarmPlaybackProviders()` one second after app startup, the registry now includes `javdb`, and the JavDB task calls the existing `loadDocumentHtmlWithBrowserWindow()` path for `https://javdb.com` and `https://missav.ai`.
- Scope check: no backend `/api/video/url` fallback was added and no `site_runtimes/` files were changed.
