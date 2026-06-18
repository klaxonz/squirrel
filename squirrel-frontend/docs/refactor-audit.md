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
- `VideoPlayer.vue`: 2708 → **2542** lines (-166 this session; -208 vs the
  corrected baseline once `useVideoRotation` is also counted).

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
| `VideoPlayer.vue` | 2708¹ | 2542 | Rotation + progress scrub + keyboard extracted. |
| `createPlayerEngine.ts` | 1050 | 991 | Types extracted; core kept cohesive. |
| `Music.vue` | ~795 | 752 | Dead QR logic removed. |
| `GlobalMusicPlayerBar.vue` | ~540 | 505 | Dead comment logic removed. |
| `engine-types.ts` | — | 106 | New (extracted types). |
| `composables/useVideoRotation.ts` | — | 79 | New (extracted from VideoPlayer). |
| `composables/useProgressScrub.ts` | — | 150 | New (progress-rail scrub). |
| `composables/usePlayerKeyboard.ts` | — | 215 | New (shortcut dispatch + lifecycle). |

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
- Remaining `VideoPlayer.vue` composables (`useSourceSync`, etc.) and `parts/`
  child components.
- Phase 3: `SiteRuntimeManager.vue` split + `lang="ts"`.
- Phase 4: `RssSources` / `Settings` / `ScheduledTasks` / `PlaylistView` /
  `LogViewer` splits.
- Phase 5: `Music` / `VideoPlay` / `Subscribed` splits + remote-seed dedup.

These are scoped and designed; the Phase-0/1/2 work above establishes the
patterns (composable extraction, type tightening, ponytail-documented
exceptions) the remaining phases follow.

## Verification

- `npm run build:check` (`vue-tsc --noEmit && vite build`): **green**.
- `npm run lint`: **0 errors**, 2 warnings (both deliberate `any` in
  `EventEmitter.ts`, documented above).
