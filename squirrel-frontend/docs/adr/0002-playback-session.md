# ADR-0002: PlaybackSession — single owner for "what's playing now"

- **Status:** Accepted (design complete; implementation pending — two PRs)
- **Date:** 2026-06-19
- **Scope:** `squirrel-frontend/src/composables/`, `src/stores/player.ts`,
  `src/components/video-player/GlobalVideoPlayerHost.vue`,
  `src/composables/useVideoPlaybackShell.ts`,
  `src/composables/useGlobalVideoPlayer.ts`
- **Follows:** ADR-0001 (StreamAdapter / StreamSink). This ADR deepens the
  *session* axis while ADR-0001 deepened the *engine* axis; the two layers are
  deliberately separate (see _Two-tier model_ below).
- **Resolves:** candidate #2 from the 2026-06-19 architecture review
  ("'what's playing now' has one owner").

## Context

Before this ADR, the answer to "what is playing right now?" was modeled in
**three places**, reconciled by a 16-source watcher:

| Home | Where | Contents |
|---|---|---|
| **A — Pinia session** | `usePlayerStore().session` (`stores/player.ts`) | 22-field reactive bag: video facts (`source` / `videoSnapshot` / `subtitles` / `externalError` / …), presentation (`title` / `uploader` / `theme` / `widescreen`), and wiring (`active` / `target` / `handlers` / `adapter`) |
| **B — runtime store** | `createPlayerRuntimeStore()` (`runtime/PlayerStore.ts`) | 30+ media-runtime fields (`playing` / `currentTime` / `volume` / `loading` / …) owned by the engine |
| **C — orchestrator / shell locals** | `usePlaybackOrchestrator` + `useVideoPlaybackShell` | 9 local `ref()`s that duplicate Home A's video facts, plus `isWidescreen` |

Home C's refs were the source of truth (data is fetched there). Home A's
session was the render input (GlobalVideoPlayerHost reads it). The two were
kept in sync by a single `watch([...16 sources...], activateGlobalVideoPlayerSession)`
pump — which is what produced the symptom the architecture review named. The
pump also carried a smell: `() => video.value?.title` was added to the source
list as a manual trigger because deep-watch on `video` could not be trusted,
exposing the "facts stored twice, reconciled by diff" pattern.

Six call sites bypassed `activateSession`/`clearSession` and wrote
`playerStore.session.xxx = …` directly (target ×2, pictureInPicture ×2,
currentVideoId ×2 — the latter two turned out to be dead code).

`pictureInPicture` was modeled in **both** Home A and Home B: the engine
raised `enterpictureinpicture` → usePlayer wrote Home B → VideoPlayer watched
Home B and emitted the event → GlobalVideoPlayerHost wrote Home A. Home A's
copy was a *delayed mirror* of Home B's, used only for the PiP-aware
`release()` decision (whether to keep the session alive when the view
unmounts).

## Decision

Collapse Home A into a single owner, `PlaybackSession`. Home B is left
untouched (ADR-0001 already closed that loop) and Home C's local refs are
turned into read-only projections of the new owner. Ship as two PRs.

### Two-tier model (explicit)

The grilling split the original "what's playing now" into two named layers,
and scoped this epic to one of them:

- **Facts layer (this epic).** *Which video, its source, its metadata, its
  related/playlist context, whether it is in PiP.* Survives across routes and
  across view mount/unmount (PiP continuity depends on this). Owner:
  `PlaybackSession`.
- **Runtime layer (out of scope; ADR-0001 territory).** *Playback progress,
  volume, buffering, current quality, controls visibility.* Derived from the
  engine and tied to the mounted `<video>` element's lifetime. Owner:
  `createPlayerEngine` + its runtime store.

The two layers meet only through `initialTime` (facts → runtime, on session
begin) and the PiP fact (runtime → facts, via the engine event). They are
not reconciled by a pump.

### The owner — `usePlaybackSession`

New module `src/composables/usePlaybackSession.ts`. App-scoped singleton
(mounted for the lifetime of the app via `GlobalVideoPlayerHost`'s host
element; not persisted to storage — a refresh rebuilds the session, by
design).

```ts
interface PlaybackSessionFacts {
  // session roots (read by isReusableFor / hydrate)
  videoId: string
  source: MediaSource | null
  video: VideoPageVideo | null
  subtitles: SubtitleTrack[]
  clipMarkers: ClipMarker[]
  initialTime: number
  externalError: ExternalErrorState | null
  externalLoading: boolean
  relatedVideos: VideoPageVideo[]
  loadingRelated: boolean
  pictureInPicture: boolean        // single source of truth (was Home A + Home B)
  // presentation projection
  title: string
  uploader: string
  theme: string
  widescreen: boolean
  hasPrev: boolean
  hasNext: boolean
  playlist: PlaylistEntry[]
  playlistIndex: number
}

interface PlaybackSession {
  facts: Readonly<PlaybackSessionFacts>            // readonly(reactive(...))
  beginNewVideo(videoId: string, seed?: VideoPageVideo | null): void
  update(patch: Partial<PlaybackSessionFacts>): void
  isReusableFor(videoId: string): boolean          // javdb actors special case folded in
  release(): void                                   // PiP-aware: keeps session if PiP, clears otherwise
  setPictureInPicture(value: boolean): void
}
```

### Key consequences

1. **One owner for the facts layer.** `usePlayerStore().session` is deleted.
   `usePlayerStore` shrinks to `playerRef` + `target` only — assembly handles
   for GlobalVideoPlayerHost, not session semantics. `target` stays in Pinia
   (it is a Teleport-anchor handle, the same kind of object as `playerRef`,
   and not a session fact).
2. **`facts` is `readonly(reactive(...))`.** Consumers read fields freely
   (`session.facts.source`, templates, computed projections); direct writes
   (`session.facts.x = y`) are rejected. Mutation goes through the verbs.
3. **The 16-source watcher evaporates.** Once the orchestrator's refs become
   `computed(() => session.facts.x)` projections, there is no second copy of
   the facts to reconcile. The pump's precondition ("facts stored twice")
   disappears. This is the analogue of ADR-0001 PR2 killing the
   reverse-driving emit: the symptom is removed by removing its cause, not by
   adding a reconciliation layer.
4. **`snapshot()` / `restore()` are *not* introduced.** The architecture
   review's original phrasing assumed the session would be serialized across
   a view unmount. It is not — the session is app-scoped and survives route
   changes by construction. The actual operations are `isReusableFor(id)`
   (does this session already represent this video?) and `beginNewVideo(id)`
   (switch to a different video). Naming follows the real operations, not the
   review's draft vocabulary.
5. **`isReusableFor` folds in the javdb special case.** Today
   `shouldRefreshJavdbSession()` is an `&&` clause inside
   `hasReusableGlobalPlaybackSession()` in the shell. It moves into the owner:
   "session matches the id *and* the facts are complete (e.g. a javdb video
   has its actors resolved)". Callers no longer know about the javdb
   exception.
6. **`release()` is PiP-aware and is the only clear path.** When a view
   unmounts: if `facts.pictureInPicture`, the session is kept (PiP
   continuity); otherwise `facts` is cleared. There is no second
   `clearSession` verb and no direct-write escape hatch.
7. **`pictureInPicture` becomes a facts-layer fact owned by the session.**
   The engine event reaches the session via `setPictureInPicture`. The
   delayed mirror through Home B → VideoPlayer emit → GlobalVideoPlayerHost
   is removed in this epic *only at the receive end* (the host calls the
   setter); the emit chain itself (a2 — deleting the VideoPlayer emit) is
   **deferred** because it touches the runtime layer (usePlayer /
   VideoPlayer) that ADR-0001 scoped out. Home B's `store.pictureInPicture`
   is kept and marked `ponytail:` as a runtime projection awaiting cleanup.

### Alternatives considered

- **Expand the existing Pinia `session` (2a).** Group the 22 fields into
  `facts` / `presentation` / `wiring` sub-objects and add verbs on top.
  Rejected: the bag's nature (anyone can write any field, watch diff across
  the whole bag) does not change by renaming. This would be "treat the
  symptom", the opposite of the ADR-0001 lesson.
- **Promote the orchestrator to the owner (2b).** Make
  `usePlaybackOrchestrator` an app-scoped singleton and delete Home A.
  Rejected: the orchestrator is coupled to *acquisition* logic
  (`useVideoDetail` / `useRelatedVideos` / `useVideoOperations`) which is
  per-view, not per-session. Forcing it global would require splitting
  acquisition from ownership — a different epic. Symmetric with the
  two-tier model: runtime is view-local, acquisition is view-local, only
  the facts need to outlive the view.
- **Keep the watcher, narrow its body (3a).** Replace
  `activateGlobalVideoPlayerSession({...})` with `session.update({...})` but
  keep 16 sources. Rejected: the redundant `() => video.value?.title`
  trigger and the deep-watch distrust remain; the pump is renamed, not
  removed.
- **Double-write (3b).** Keep orchestrator refs as the source, call
  `session.setX` at every mutation point. Rejected: 8+ mutation sites in
  the orchestrator, each a chance to forget the second write, with no test
  net (see Testability). 3c makes refs projections, so the write happens
  once.
- **Restore the session across unmount via `snapshot()/restore()` (4b).**
  Rejected naming: the session does not unmount, so there is nothing to
  restore. The verbs (`isReusableFor` / `beginNewVideo` / `release`) name
  the real operations.

## Implementation plan (two PRs)

The split mirrors ADR-0001: a pure structural PR that can be byte-compared,
then a control-flow PR that inverts the data-flow direction. The boundary is
drawn at "does the data-flow direction change?". PR1 does not.

### PR1 — seam + mutation收口 (zero behavior change)

Structural. The reconciler pump still runs; it just writes to the new owner
through a verb instead of to the old bag via `Object.assign`.

- New module `composables/usePlaybackSession.ts` with the interface above,
  plus a contract test suite
  (`composables/usePlaybackSession.test.ts`) — the project's first test file.
- Add vitest (devDependency + `vitest.config.ts` + `test` script). No
  happy-dom, no @vue/test-utils: the contract test is a pure state machine.
- Move the 22 fields from `playerStore.session` to `session.facts` (readonly
  wrapper). `usePlayerStore` shrinks to `playerRef` + `target`.
- Rename all read sites `playerStore.session.*` → `session.facts.*`
  (GlobalVideoPlayerHost, useVideoPlaybackShell, useGlobalVideoPlayer).
- Rewire the 16-source watcher's body to call `session.update(patch)` (the
  pump still exists; PR2 deletes it).
- Replace the 6 direct writes with verbs/setters: PiP handlers call
  `session.setPictureInPicture(...)`, target stays on Pinia.
- Delete the 2 dead wrappers
  (`setGlobalVideoPlayerPictureInPicture`,
  `setGlobalVideoPlayerCurrentVideoId` — zero callers).
- PiP truth-source migration (6c, receive-end only): GlobalVideoPlayerHost's
  `@enterpictureinpicture` / `@leavepictureinpicture` handlers call the
  setter instead of assigning the field. The emit chain itself is preserved
  (a2 deferred).
- Mark Home B `runtime/PlayerStore.ts` `pictureInPicture` field with a
  `ponytail:` comment: runtime projection, truth source moved to
  PlaybackSession, field deletion + emit-chain short-circuit deferred to a
  runtime-layer follow-up.

Verification bar: `test + typecheck + lint + build:check` green, plus manual
smoke (play / cross-route / PiP) confirming zero behavior change. The PR1
contract test is the safety net for PR2.

### PR2 — data-flow inversion (control-flow change)

- `usePlaybackOrchestrator`: replace its `ref()` declarations for video facts
  with `computed(() => session.facts.x)` projections. Fetch results call
  `session.update(...)` directly.
- `useVideoPlaybackShell`: delete the 16-source watcher and
  `hydrateFromGlobalPlaybackSession`. `onMounted` / route watch use
  `session.isReusableFor(id)` (no-op if reusable, computed projections take
  over) or `session.beginNewVideo(id)` + `loadAndPlayById`.
- The `hasReusableGlobalPlaybackSession` / `shouldRefreshJavdbSession` logic
  collapses into `session.isReusableFor`.

Verification bar: same tooling green + the PR1 contract test still green
(this is the safety net for the inversion) + focused manual smoke on
cross-route reuse, the javdb special case, and PiP-then-return continuity.

## Testability

The frontend had no test runner before this ADR (no `test` script, zero test
files). This epic introduces vitest and the first test — but only for the
new owner, because `PlaybackSession` is a pure state machine (no DOM, no
engine, no async I/O) and therefore the cheapest possible first test target.
The test pins the Q4/Q5/Q6 design decisions as executable documentation:

- `beginNewVideo(id)` clears stale facts (old `source` / `videoSnapshot` /
  `externalError` reset, `externalLoading` set).
- `update(patch)` applies a partial patch and leaves unmentioned fields
  intact.
- `isReusableFor(id)` — same id + has any state → true; same id + javdb url
  + no actors → false (forces refresh); different id → false.
- `release()` — PiP on → facts preserved; PiP off → facts cleared.
- `facts` is `readonly` — direct assignment is rejected.
- `setPictureInPicture(v)` updates `facts.pictureInPicture`.

The ADR-0001 `FakeStreamAdapter` layer-1 contract test remains **deferred**.
It belongs to the runtime layer, which this epic explicitly scopes out; it
will land with the runtime-layer follow-up that also removes Home B's
`pictureInPicture` mirror and short-circuits the emit chain.

## Consequences for future work

- **Runtime-layer cleanup (deferred).** Home B's `store.pictureInPicture`
  field, the VideoPlayer `enterpictureinpicture` / `leavepictureinpicture`
  emits, and the `FakeStreamAdapter` contract test all belong to a single
  follow-up epic on the runtime layer. This ADR marks them `ponytail:`
  rather than silently leaving them.
- **`useGlobalVideoPlayer` audit (deferred).** This epic deletes the 2 dead
  wrappers it identified; a fuller audit of the 12-symbol surface is out of
  scope.
- **`hydratePlaybackState` simplification.** Once the orchestrator refs
  become projections (PR2), `hydratePlaybackState` in the orchestrator
  either shrinks to a `session.update(...)` forward or is deleted entirely.
  That judgement is made in PR2, not here.
