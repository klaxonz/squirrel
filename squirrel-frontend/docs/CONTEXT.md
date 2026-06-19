# Frontend Domain Glossary (CONTEXT.md)

Ubiquitous language for the Vue 3 frontend. Terms here name seams and
concepts that the architecture review and ADRs reference. Add a term when a
deepened module is named after a concept not already here; sharpen a term in
place when the conversation tightens its meaning.

## Video player engine

The playback core under `src/components/video-player/core/`. Owns the
`<video>` element, transport state, and the orchestration of stream loading,
quality, subtitles, and progress. Implemented as one closure-based factory
(`createPlayerEngine`) plus extracted algorithm modules (error-recovery,
plugin management). See ADR-0001 for the adapter / sink split.

### StreamAdapter

An independent module that knows how to load and control one streaming
technology (HLS via hls.js, DASH via dashjs, DASH via shaka-player). The
engine instantiates one adapter per source and drives it through a fixed
interface; it never reaches into a library by name. Three adapters justify
the seam.

Interface: `onSourceChange` / `setQuality` / `recoverPlayback` / `destroy`,
plus four optional codec-family methods present only on the DASH adapters.
A stream adapter is **not** a `PlayerPlugin` — it does not register with
`PluginManager` and does not implement lifecycle hooks.

### StreamContext

The narrow input handed to a `StreamAdapter` at construction: a `videoElement`
getter (lazy — the element may attach after the adapter is built), a logger,
and per-adapter options. Replaces the fat `PluginContext` (~20 fields) that
plugins used to receive. An adapter has no other way to read engine state.

### StreamSink

The narrow output a `StreamAdapter` uses to hand state back to the engine:
`qualitiesResolved` (one-shot, after a source loads), `qualityChanged`
(recurring, on ABR / manual switches), `loadingStateChanged` (replaces
`emit('waiting')` / `emit('canplay')`), and `error`. This is the **only**
channel by which an adapter drives the engine — there is no event-bus
reverse-driving and no `setQuality` round-trip. The engine owns quality
strategy (user preference, auto-quality) on top of the facts the sink
delivers; the adapter owns implementation detail (e.g. DASH codec-family
default selection) and reports the result through `qualitiesResolved`.

### PlayerPlugin (non-stream)

Lifecycle-driven modules that remain on `PluginManager`: today `SubtitlesPlugin`
and `AnalyticsPlugin`. They react to player events (`onPlay`, `onTimeUpdate`,
`onError`, …) via the manager's event forwarding. Stream technology used to
live here too; it was extracted into `StreamAdapter` because its plugins
implemented almost none of the lifecycle hooks and were driven by name-keyed
casts instead.

### ErrorRecovery

An externalized algorithm module (`core/error-recovery.ts`) that decides how
the engine responds to playback errors (retry, quality fallback, alternative
source). Reads engine state through a 28-field `ErrorRecoveryDeps` bag,
including a `getStreamAdapter` accessor (it no longer depends on
`PluginManager`).

## PlaybackSession (facts layer)

The single owner of "what is playing right now": which video, its source,
its metadata, its related/playlist context, and whether it is in PiP.
App-scoped singleton (`composables/usePlaybackSession.ts`); survives route
changes and view mount/unmount by construction (it does not unmount), which
is what PiP continuity depends on. See ADR-0002.

The session exposes `facts` — a `readonly(reactive(...))` view of the
session state — and four verbs that are the **only** mutation paths:
`beginNewVideo(id, seed?)`, `update(patch)`, `isReusableFor(id)`, and
`release()`. There is no `snapshot()` / `restore()` pair: those names were
drafted in the architecture review under the assumption that the session
would be serialized across a view unmount; it is not.

### Two-tier model (PlaybackSession vs. runtime store)

"Playback state" was originally one question; the grilling split it into
two named layers so each can have one owner:

- **Facts layer — `PlaybackSession`.** *Which* video. Survives routes. This
  epic (ADR-0002).
- **Runtime layer — `createPlayerEngine` + `runtime/PlayerStore.ts`.** *How*
  it's playing (progress, volume, buffering, current quality). Tied to the
  mounted `<video>` element's lifetime. ADR-0001 already closed this loop.

The two layers meet only through `initialTime` (facts → runtime, on session
begin) and the PiP fact (runtime → facts, via the engine event). They are
not reconciled by a pump.

### `isReusableFor` / javdb special case

The "is this session already representing this video?" check, folded into
the owner. It subsumes what used to be `hasReusableGlobalPlaybackSession` +
`shouldRefreshJavdbSession` in the shell: "same id *and* the facts are
complete (e.g. a javdb video has its actors resolved)". Callers no longer
know about the javdb exception.

### `release()` (PiP-aware)

The only clear path. When a view unmounts: if `facts.pictureInPicture`, the
session is kept (PiP continuity); otherwise `facts` is cleared.

## (other frontend concepts — to be added as deepened modules are named)

The music player store and RSS reader are flagged as future deepening
candidates in the architecture review but have not yet been grilled; their
terms are not stabilized here.
