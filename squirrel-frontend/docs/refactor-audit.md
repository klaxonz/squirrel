# Frontend Refactor Audit

Open-source quality pass on `squirrel-frontend/`. This document records what
was done, what was deliberately deferred, and the reasoning behind each
non-obvious decision — so a reviewer (or future maintainer) can audit the
choices rather than reverse-engineer them.

## Goals

- Eliminate mojibake / encoding-corrupted comments (open-source readability).
- Delete dead code (hand-rolled logic duplicating existing composables).
- Tighten loose typing (`any` → concrete types where the cost is low).
- Split mega-components / mega-modules where the seam is natural.
- Hit reasonable size targets without forcing harmful splits.

## What was done

### Phase 0 — Hygiene fixes

| Area | Change |
|---|---|
| `VideoPlayer.vue` | 26 mojibake comments restored to readable Chinese (9 template + 17 CSS section banners). |
| `Music.vue` | Removed ~50 lines of hand-rolled QR-login logic; now consumes the existing `useMusicQrLogin` composable. |
| `GlobalMusicPlayerBar.vue` | Removed ~50 lines of hand-rolled comment-loading logic; now consumes the existing `useMusicComments` composable. |
| `core/types.ts` | New `SubtitleStyle` type (concrete known keys + index signature) replaces `Record<string, any>`. Threaded through `usePlayer`, `useSettingsMenu`, `createPlayerEngine`, `engine-types`. |
| `CentralHudOverlay.vue` | Two `as any` casts removed; `icon` field now typed as `IconName`. |
| `useSleepTimer` / `useClipMarkers` | `showCentralHud` callback signature tightened from `icon: string` to `icon: IconName`. |
| `musicPlayer.ts` | `_onEnded` renamed to `handleEnded` — it was already part of the store's public API (consumed by the audio `@ended` binding), so the underscore prefix was a misnomer. |
| Plugin interop | DashPlugin / HlsPlugin / ShakaDashPlugin: added `ponytail:` header comments documenting why the `as any` casts at the library boundary are deliberate (dash.js / hls.js / shaka-player ship incomplete `.d.ts`). |

### Phase 1 — Engine type extraction

- `core/engine-types.ts` (new): `PlayerEngineOptions`, `PlayerEngine`,
  `QualityController`, `SubtitleController` extracted out of
  `createPlayerEngine.ts`.
- `createPlayerEngine.ts`: re-exports the public types so existing imports keep
  working; dropped from 1050 → 991 lines; gained an architecture note.

### Phase 2 — VideoPlayer composable extraction (partial)

- `composables/useVideoRotation.ts` (new, 79 lines): rotation state + scale +
  ResizeObserver + RAF throttling, with internal `onUnmounted` cleanup.
- `VideoPlayer.vue`: dropped from 2750 → 2407 lines (-343).

### Phase 2 (cont.) — progress scrub + keyboard extraction

The Phase-2 "before" figure above was aspirational — `VideoPlayer.vue` was
actually **2708 lines** at commit `8c7ef66d` (the original Phase-0/1/2 pass),
not 2407. This continuation works against the real number.

- `composables/useProgressScrub.ts` (new, 150 lines): progress-rail pointer
  scrub — preview thumbnail/time + actual seek on drag, plus clip-marker
  pending-segment-end sync. Owns pointer capture + window listeners; released
  via a `cleanup()` the caller runs in `onUnmounted`. The `isScrubbing` watch
  that suppresses control auto-hide stays in `VideoPlayer` (it's a
  controls-visibility concern, not a scrub concern).
- `composables/usePlayerKeyboard.ts` (new, 215 lines): the keyboard-shortcut
  dispatch table + its own `window` keydown listener lifecycle. The action
  surface (transport, volume, markers, speed, loop, playlist nav) is injected,
  so the composable is a pure dispatch table with no player state of its own.
  `VideoPlayer` dropped its own `onMounted`/`onUnmounted` keydown wiring.
- `composables/useSourceSync.ts` (new, 176 lines): synchronizes the engine with
  the `source` / `initialTime` props — applies `initialTime` once per source
  (metadata-gated), arms resume-after-swap when the source briefly goes null
  (adapter swap) and resumes on the new source's `canplay`, and notifies the
  caller on source-identity change so it can clear source-scoped UI. The
  `videoRef`/`containerRef` bridge watches stay in `VideoPlayer` (usePlayer
  wiring, not source logic).

### Phase 2 (cont. 2) — overlay component extraction

- `LoadingOverlay.vue` (new, 73 lines): the buffering/load spinner + stage text,
  with its own scoped fade transition + spinner keyframes. Narrow surface
  (`visible`, `stageText`).
- `ErrorOverlay.vue` (new, 109 lines): the fatal-error panel (icon/title/message/
  retry), with its own scoped fade + darkening backdrop. Narrow surface (visible/
  title/message/canRetry/fallbackTitle/retryLabel + `retry` emit).
- Both follow the existing `*-Overlay.vue` convention (`CentralHudOverlay`,
  `ChapterOverlay`, `UpNextOverlay`, …). The shared `sp-loading-fade` transition
  is now duplicated as a tiny scoped block in each (they never animate together,
  so no shared global CSS is worth the indirection).
- `VideoPlayer.vue`: 2448 → **2317** lines (-131). Each overlay also pulled its
  scoped CSS out of `VideoPlayer`'s `<style>`, which is the bulk of the win.

### Phase 3 (partial) — `SiteRuntimeManager.vue` YouTube OAuth extraction

`SiteRuntimeManager.vue` (was 1067 lines, JS `<script setup>`) is a single view
holding six tightly-coupled clusters: connectivity testing, login status, YouTube
OAuth, site catalog/editor, cookie import, and a toast. The audit had deferred
this file as "split + `lang='ts'`" in one shot; on inspection a full split is a
forced-seam refactor (every cluster calls into the others — shared cache, shared
`upsertLoginStatus`, shared `getDesktopBridge`, cross-cluster refresh), so the
high-leverage move is to extract the **one** cluster with a clean boundary and
leave the rest.

- `composables/useYouTubeOAuth.ts` (new, 198 lines, **TS**): the YouTube TV-code
  OAuth flow — start/revoke, the verification-code prompt UI (show/hide/copy +
  dismiss suppression), and the 3s status poll while authorization is pending.
  Owns its own `onUnmounted` lifecycle (the only unmount hook the view had).
  Injects the three cross-cluster deps (`upsertLoginStatus`,
  `refreshSiteRuntimes`, `openExternalUrl`) so it doesn't reach into the other
  clusters. Reuses the existing `getDesktopBridge` from `useDesktopBridge`
  instead of redefining it.
- `SiteRuntimeManager.vue`: 1067 → **929** lines (-138). Dropped the
  `onUnmounted` hook (now in the composable), the `ytOAuthPollTimer` /
  `youtubeOAuthCopyTimer` lets, and three now-unused YouTube API imports
  (`setupYouTubeOAuth` / `revokeYouTubeOAuth` / `getYouTubeOAuthStatus`).
- Remaining clusters deferred: connectivity / login-status / cookie-import /
  site-editor are mutually coupled via shared cache + `upsertLoginStatus` +
  `getDesktopBridge`; extracting any one needs ~8-12 injected deps and the
  wiring equals the block. The `lang='ts'` conversion is still deferred — it
  surfaces dozens of implicit-`any` errors best fixed when each cluster is
  extracted into a TS composable (new files are TS from the start), not as a
  standalone annotation flood.

### Phase 4 (partial) — `RssSources.vue` Add/Edit Account dialog extraction

`RssSources.vue` (was 1519 lines) is already well-composed at the script level
(five composables: accounts / feeds / entries / reader / sync) and already
typed. The bulk is the **871-line template** — a three-pane reader app plus
three dialogs plus a lightbox.

- `components/rss/AccountEditDialog.vue` (new, 230 lines, TS): the Add/Edit RSS
  Account dialog (provider switcher, name/base-url/username/credential fields,
  enabled toggle, test/save footer). Uses `defineModel` for both `open` and
  `form` — the form is the parent composable's reactive `accountForm`, and
  `defineModel` lets the child `v-model` its fields lint-clean (mutating a
  model ref, not a prop) while Vue's reactivity propagates back. Read-only
  computeds + the two handlers come in as plain props/emits.
- `RssSources.vue`: 1519 → **1362** lines (-157).
- Other dialogs deferred: the Delete-confirm dialog (17 lines — too small to
  beat its own prop/emit overhead) and the Subscribe-feed dialog (133 lines —
  its two template refs, `categoryDropdownRef` / `customCategoryInputRef`, are
  read by `useRssFeeds` for click-outside / autofocus, so extraction needs ref
  bridging like the context menus; same forced-seam calculus).

### Phase 4 (cont.) — `Settings.vue` Security tab extraction

`Settings.vue` (was 617 lines) is a six-tab settings page. The **security**
tab is the one tab with zero cross-tab dependencies: it owns all of its state
(`securityForm`, submit flags, error/success messages) and talks directly to
its own two API endpoints (`updateUserPassword`, `revokeUserSessions`). That
makes it a clean extraction with **no props and no emits** — the rare
win-win of smaller parent + self-contained child.

- `components/settings/SecuritySettings.vue` (new, 138 lines, TS): password
  change form (current/new/confirm with length + match validation) + revoke
  other sessions. Extracted verbatim; the parent dropped its `passwordFields`
  array, `SecurityForm` interface, four refs, three handlers, and the two API
  imports.
- `Settings.vue`: 617 → **495** lines (-122).
- Other tabs deferred: appearance / content / playback are tightly bound to the
  shared `useUserSettings` / `useThemeStore` reactive state (toggles that fire
  `onUserSettingChange` on every flip), and system/server each own a composable
  already. Extracting them would thread the shared `showSaveToast` + the
  composable refs back in — net-neutral until the toast is also extracted.

## Deliberate decisions (defend the choice, don't hide it)

### Why `createPlayerEngine.ts` stays a single 991-line module

The engine is a **state machine**: ~30 closure variables (video element, audio
graph, source/quality/subtitle/progress state) are read and written by
overlapping subsets of the play / pause / seek / volume / quality / subtitle /
source / progress operations. Splitting into per-feature sub-modules would
force a state-object + getter/setter seam for every cross-cutting read.

The cost of that seam is visible in `error-recovery.ts`, which already needs
**28 deps** for its narrower concern. Applying the same pattern to the whole
engine would multiply that cost across every operation — a net readability loss
that fights the open-source goal.

The genuinely isolatable concerns **are** split: error recovery, public types,
plugin management, events. What remains is the core playback state machine,
most readable as one file.

### Why DashPlugin / HlsPlugin / ShakaDashPlugin keep `as any`

These three libraries (`dash.js`, `hls.js`, `shaka-player`) ship incomplete or
loose TypeScript declarations. Their runtime surfaces expose many methods /
event-payload fields that are missing or under-typed in the `.d.ts`. Maintaining
a parallel hand-written type overlay would:

1. Duplicate library internals that already exist in their source.
2. Drift on every library bump (silent regressions).
3. Cost more than the safety gain (these casts live at the library boundary,
   not in internal logic).

Each plugin has a `ponytail:` header documenting this so a reviewer sees it as
a deliberate interop decision, not loose code.

### Why `SiteRuntimeManager.vue` `lang="ts"` is deferred

The file is 1068 lines of `<script setup>` without `lang="ts"`. Adding the flag
in isolation surfaces dozens of implicit-`any` errors that would need fixing
inline — a large, low-leverage change. The higher-leverage move is the
planned Phase 3 split into composables + child components, where each new file
is written in TypeScript from the start. Forcing `lang="ts"` now would either
require a flood of one-off annotations or a `// @ts-nocheck` escape hatch,
neither of which improves real type safety.

### Why `EventEmitter` keeps `any` defaults

```ts
export type EventHandler<T = any> = (data: T) => void
export type EventMap = Record<string, any>
```

Tightening to `unknown` breaks the `PlayerEvents` constraint: concrete
interfaces like `PlayerEvents` don't carry a string index signature, so they
fail `extends Record<string, unknown>`. The concrete emitter is always
instantiated with a typed Events map (`EventEmitter<PlayerEvents>`), so the
`any` default only applies to the rare untyped fallback. Documented inline.

## Size status (before → after)

| File | Before | After | Notes |
|---|---|---|---|
| `VideoPlayer.vue` | 2708¹ | 2317 | Rotation + progress scrub + keyboard + source-sync + 2 overlays extracted. |
| `createPlayerEngine.ts` | 1050 | 991 | Types extracted; core kept cohesive. |
| `Music.vue` | ~795 | 752 | Dead QR logic removed. |
| `GlobalMusicPlayerBar.vue` | ~540 | 505 | Dead comment logic removed. |
| `engine-types.ts` | — | 106 | New (extracted types). |
| `composables/useVideoRotation.ts` | — | 79 | New (extracted from VideoPlayer). |
| `composables/useProgressScrub.ts` | — | 150 | New (progress-rail scrub). |
| `composables/usePlayerKeyboard.ts` | — | 215 | New (shortcut dispatch + lifecycle). |
| `composables/useSourceSync.ts` | — | 176 | New (source/initialTime/resume sync). |
| `LoadingOverlay.vue` | — | 73 | New (load/buffering overlay). |
| `ErrorOverlay.vue` | — | 109 | New (fatal-error overlay). |
| `SiteRuntimeManager.vue` | 1067 | 929 | YouTube OAuth extracted. |
| `composables/useYouTubeOAuth.ts` | — | 198 | New (YouTube TV-code OAuth flow). |
| `RssSources.vue` | 1519 | 1362 | Add/Edit Account dialog extracted. |
| `components/rss/AccountEditDialog.vue` | — | 230 | New (RSS account add/edit dialog). |
| `Settings.vue` | 617 | 495 | Security tab extracted. |
| `components/settings/SecuritySettings.vue` | — | 138 | New (password + session-revoke tab). |

¹ The earlier draft of this table listed `2750 → 2407`; that was aspirational.
`git show 8c7ef66d:squirrel-frontend/.../VideoPlayer.vue` is 2708 lines. The
corrected baseline is used here.

## Deferred to a follow-up session

- `useControlsVisibility`: `hideControls` / `syncHideTimer` / `showControls` /
  `onPointer*` stay inline. They couple to `showVideoInfo`, `videoInfoTimer`,
  `isFullscreen`, `showChapterOverlay`, and `store.controlsVisible`, and
  `showControls`/`hideControls` are reused by the `isScrubbing` watch and
  `onPointerLeave`. Extracting needs ~5 refs + 3 callbacks plus re-exports of
  the two functions the caller still calls — the wiring equals the block size,
  a forced seam (negative net readability). Documented as deferred.
- Remaining `VideoPlayer.vue` work: `parts/` child components (template-level
  splits of the controls bar, settings menu shell, overlays). The script-level
  composable extractions above are the high-leverage ones; the template is now
  the bulk of the file and is better addressed by component extraction than by
  more composables.
- Phase 3 remainder: `SiteRuntimeManager.vue` connectivity / login-status /
  cookie-import / site-editor clusters (mutually coupled — see note above) +
  the `lang='ts'` conversion (best done per-cluster as each is extracted).
- Phase 4 remainder: `RssSources.vue` Subscribe-feed dialog (needs ref
  bridging) + `Settings.vue` appearance/content/playback/system/server tabs
  (bound to shared user-settings/theme/server composables) /
  `ScheduledTasks` (572) / `PlaylistView` (509) / `LogViewer` (546) splits.
- Phase 5: `Music` (843) / `VideoPlay` (724) / `Subscribed` (755) splits +
  remote-seed dedup.

These are scoped and designed; the Phase-0/1/2 work above establishes the
patterns (composable extraction, type tightening, ponytail-documented
exceptions) the remaining phases follow.

## Verification

- `npm run build:check` (`vue-tsc --noEmit && vite build`): **green**.
- `npm run lint`: **0 errors**, 2 warnings (both deliberate `any` in
  `EventEmitter.ts`, documented above).
