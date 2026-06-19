# Handoff: ADR-0002 PlaybackSession — PR1 (seam + mutation收口)

**Date:** 2026-06-19
**Branch:** `fix/bug` (PR1 not yet committed; stay on this branch)
**Repo:** `D:\Code\init\squirrel` (frontend at `squirrel-frontend/`)
**ADR:** `squirrel-frontend/docs/adr/0002-playback-session.md`

---

## What this is

ADR-0002 candidate #2 from the 2026-06-19 architecture review: "what's playing
now" had three owners (Pinia `session` / runtime `PlayerStore` / orchestrator
+ shell locals) reconciled by a 16-source watcher. The grilling (9 questions,
all resolved — see the ADR's _Alternatives considered_) decided:

- **Two-tier model.** Facts layer (which video — this epic) is separated from
  runtime layer (how it's playing — ADR-0001 territory, out of scope).
- **One owner.** New `usePlaybackSession` owns the facts; Pinia `usePlayerStore`
  shrinks to assembly handles (`playerRef` / `target` / `adapter` / `handlers`).
- **Four verbs.** `beginNewVideo` / `update` / `isReusableFor` / `release`.
  No `snapshot()`/`restore()` — the session is app-scoped and never unmounts.
- **`facts` is `readonly(reactive(...))`.** Mutation only through the verbs.
- **PiP truth-source migration (6c, receive-end).** GlobalVideoPlayerHost's
  PiP emit handlers call `session.setPictureInPicture(...)` instead of
  assigning the field. The emit chain itself (a2) is deferred.
- **First test.** vitest introduced; PlaybackSession contract test is the
  project's first test file. FakeStreamAdapter (ADR-0001's debt) still
  deferred.

## Where PR1 leaves things

**PR1 is structural, zero behavior change** — the same 16-source watcher still
runs; its body just writes to the new owner via `session.update()` instead of
to the old bag via `Object.assign`. Verified green:
`test` (12 passing) + `typecheck` + `lint` (only 2 pre-existing EventEmitter
warnings) + `build:check`.

Files touched (excluding `package-lock.json`):

| File | Change |
|---|---|
| `composables/usePlaybackSession.ts` | **NEW** — the owner. Module-scoped singleton; `facts` readonly; 4 verbs + `setPictureInPicture`; `__resetPlaybackSessionForTests` escape hatch. |
| `composables/usePlaybackSession.test.ts` | **NEW** — 12 contract tests (begin/update/isReusableFor/release/readonly/setPiP). |
| `vitest.config.ts` | **NEW** — minimal config, `@` alias, no DOM env. |
| `composables/useGlobalVideoPlayer.ts` | Facade over PlaybackSession + slimmed Pinia. Public surface preserved (same names) so call sites don't change. Peels `target`/`adapter`/`handlers` off the payload to Pinia; routes facts to `session.update()`. Dead wrappers deleted. |
| `stores/player.ts` | Session bag deleted. Now `playerRef` + `target` + `adapter` + `handlers` (the latter two ponytail: PR2 relocates). |
| `components/video-player/GlobalVideoPlayerHost.vue` | Reads `session.facts.*` + Pinia handles. `active` flag gone — gate is now `facts.videoId !== ''`. PiP handlers call `session.setPictureInPicture`. |
| `components/video-player/VideoPlayer.vue` | Playlist reads → `playbackSession.facts`. Dropped unused `usePlayerStore` import. |
| `components/video-player/PlaylistPanel.vue` | `PlaylistEntry` import → `@/types/playerSession`. |
| `composables/useVideoPlaybackShell.ts` | Field renames (`currentVideoId`→`videoId`, `videoSnapshot`→`video`) in the reuse/hydrate helpers + watcher payload. Watcher body still calls `activateGlobalVideoPlayerSession` (facade routes it). |
| `types/playerSession.ts` | Orphaned `PlayerSessionState` interface removed (re-exported as alias from the facade). Cleaned unused imports. |
| `components/video-player/runtime/PlayerStore.ts` | `pictureInPicture` field marked `ponytail:` (runtime projection; truth source moved; field + emit chain deletion deferred to a2). |
| `docs/adr/0002-playback-session.md` | **NEW** — the ADR (9-question design record). |
| `docs/CONTEXT.md` | Vocabulary: PlaybackSession, two-tier model, isReusableFor, release. |

## What PR2 does (the next session's job)

PR2 is the **control-flow inversion** — the data-flow direction reverses.
Risk concentrates here, which is why it's a separate PR.

1. **`usePlaybackOrchestrator` — refs → computed.** Its `ref()` declarations
   for video facts (`video`, `playbackSource`, `subtitleTracks`,
   `externalError`, `isResolvingPlayback`, `relatedVideos`, `loadingRelated`)
   become `computed(() => session.facts.x)` projections. Fetch results call
   `session.update(...)` directly instead of mutating the local ref.
2. **`useVideoPlaybackShell` — delete the 16-source watcher.** It exists only
   to reconcile Home C → Home A; once Home C *is* the projection of the owner,
   there is nothing to reconcile. `onMounted` / route watch switch to:
   ```ts
   if (session.isReusableFor(videoId)) {
     /* no-op: computed projections reflect the surviving session */
   } else {
     session.beginNewVideo(videoId, seed)
     await loadAndPlayById(videoId, seed)
   }
   ```
3. **Collapse reuse helpers.** `hasReusableGlobalPlaybackSession` /
   `shouldRefreshJavdbSession` / `isSameGlobalPlaybackSession` in the shell
   collapse into `session.isReusableFor(id)` (which already encodes the javdb
   special case — see the test).
4. **`hydrateFromGlobalPlaybackSession` deletes.** Hydrate existed to pump
   Home A facts back into Home C refs; with C as projections, no pump needed.
5. **`hydratePlaybackState` in the orchestrator** either shrinks to a
   `session.update(...)` forward or is deleted — judge during PR2.
6. **`adapter` / `handlers` ponytail cleanup** (optional in PR2 or a PR3):
   these wiring fields currently sit on Pinia. Once the orchestrator is the
   direct emit target (no VideoPlayer emit → host → Pinia.handlers round-trip)
   they can move into the host or be deleted.

## PR2 verification bar

- `test + typecheck + lint + build:check` green.
- **The PR1 contract test must still pass unchanged** — it's the safety net
  for the inversion (if `isReusableFor`/`release`/`beginNewVideo` semantics
  drift, the test catches it).
- **Focused manual smoke** (the behaviors the watcher used to drive):
  1. Cross-route reuse: VideoPlay A → VideoPlay B with the *same* video id
     does not re-fetch.
  2. Javdb special case: a javdb video whose actors are unresolved forces a
     refresh even when the id matches.
  3. PiP continuity: enter PiP, navigate away from VideoPlay, navigate back —
     playback continues without a reload.
  4. New video load: navigating to a different video id triggers a fresh
     fetch (no stale source leak).

## Key files to re-read before PR2

- `squirrel-frontend/docs/adr/0002-playback-session.md` — the design record.
- `squirrel-frontend/src/composables/usePlaybackSession.ts` — the owner's API
  (PR2 consumes it; does not change it).
- `squirrel-frontend/src/composables/usePlaybackOrchestrator.ts` — the file
  PR2 rewrites most heavily. Its `ref()`s at lines 115-119 + the
  `hydratePlaybackState` at 261-285 are the inversion targets.
- `squirrel-frontend/src/composables/useVideoPlaybackShell.ts` — the watcher
  at 200-292 is what PR2 deletes.

## Working style (unchanged from ADR-0001 handoff)

- Two-PR discipline: PR1 structural + revertable (this one), PR2 control-flow.
- Verification bar: `test + typecheck + lint + build:check` all green.
- Commit on `fix/bug`, no feature branch.
- The user reads Chinese; mixed Chinese/English in conversation is fine;
  code identifiers and docstrings are English.
