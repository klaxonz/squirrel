# ADR-0001: Stream adapter seam and sink-based quality delivery

- **Status:** Accepted (design complete; implementation pending — two PRs)
- **Date:** 2026-06-19
- **Scope:** `squirrel-frontend/src/components/video-player/`
- **Supersedes / refines:** `docs/refactor-audit.md` "Why `createPlayerEngine.ts`
  stays a single 991-line module" (unchanged) and the candidate-1 entry in the
  2026-06-19 architecture review.

## Context

The video player ships three streaming technologies behind three "plugins"
(`HlsPlugin` / `DashPlugin` / `ShakaDashPlugin`) that all implement
`PlayerPlugin` but satisfy an **undeclared** interface. The engine and
error-recovery selected the right one by branching on `currentSourceType` +
`source.playbackEngine === 'shaka'` and then casting via
`pluginManager.get<T>('hls' | 'dash' | 'shaka-dash')`. That dispatch was
duplicated in three places, and the runtime duplicated it a fourth time to
decide whether the codec-family UI applied.

Worse, the engine↔adapter relationship was driven **both ways through the
event bus**: adapters called `context.emit('qualitiesloaded')`,
`context.registerQualities(...)`, `context.registerCurrentQualityId(...)`,
`context.setQuality(defaultId)` (a round-trip back into the engine), and — for
DASH/Shaka — `context.emit('waiting')` / `context.emit('canplay')`, which
triggered the engine's loading-state machine through a specially-intercepted
`emit` override in `PluginContext`.

The architecture review (2026-06-19) flagged this as candidate #1: a real
seam (three adapters) with no named interface and leaking dispatch.

## Decision

Split the stream-loading concern out of the plugin system entirely, behind
two new interfaces — `StreamAdapter` (input/control) and `StreamSink`
(output/callbacks) — with a narrow `StreamContext` as the only engine state
an adapter can read. Ship as two PRs.

### Interfaces

```ts
interface StreamContext {           // engine → adapter (construction input)
  readonly videoElement: () => HTMLVideoElement | null   // lazy getter
  readonly logger: PlayerLogger
  readonly options?: Record<string, unknown>
}

interface StreamSink {              // adapter → engine (delivery callbacks)
  qualitiesResolved(qualities: QualityLevel[], currentId: string | number | null): void
  qualityChanged(quality: { id: string | number; label: string; auto: boolean }): void
  loadingStateChanged(isLoading: boolean): void
  error(error: PlayerError): void
}

interface StreamAdapter {           // engine → adapter (control)
  onSourceChange(source: MediaSource, sink: StreamSink): void
  setQuality(quality: QualitySelectionRequest): void
  recoverPlayback(error: PlayerError, ctx: PlaybackRecoveryContext): PlaybackRecoveryAction | Promise<PlaybackRecoveryAction>
  destroy(): void
  getAvailableCodecFamilies?(): string[]   // DASH/Shaka only
  getSelectedCodecFamily?(): string
  getCurrentCodecFamily?(): string | null
  setCodecFamily?(id: string): void
}
```

### Key consequences

1. **Stream adapters are no longer `PlayerPlugin`s.** They are not registered
   with `PluginManager` and do not implement lifecycle hooks. `PluginManager`
   keeps managing `SubtitlesPlugin` and `AnalyticsPlugin` (which genuinely use
   the `onPlay` / `onTimeUpdate` / `onError` forwarding).
2. **The engine instantiates adapters itself.** It caches
   `currentStreamAdapter` + `currentAdapterType`; on `loadSource` it reuses
   the adapter when the source type is unchanged and destroys + rebuilds it
   otherwise (matching today's "adapter instance lives, internal library
   instance is rebuilt per source" semantics).
3. **No event-bus reverse-driving.** The only channel from adapter to engine
   is the four `StreamSink` methods. The engine's intercepted-`emit` hack
   (the `waiting` / `canplay` special cases in `PluginContext`) is deleted.
4. **The quality round-trip is gone.** Today an adapter calls
   `context.setQuality(defaultId)` to ask the engine to set a default; the
   engine then calls `adapter.setQuality(...)`. Under this ADR the adapter
   reports a *fact* (`qualitiesResolved(qs, currentId)` — `currentId` already
   reflects any internal default the adapter chose, e.g. DASH codec family),
   and the engine applies *strategy* (user preference, auto-quality) on top,
   calling `adapter.setQuality(...)` only when it decides to override. One
   direction, no loop.
5. **DASH codec-family asymmetry becomes optional methods, not runtime
   branches.** The runtime asks `adapter.getAvailableCodecFamilies?.()`
   instead of branching on `sourceType === 'dash'`.
6. **`error-recovery` gets a `getStreamAdapter` accessor and drops its
   `pluginManager` dependency.** `ErrorRecoveryDeps` stays at 28 fields
   (−`pluginManager`, +`getStreamAdapter`); net neutral, but the module no
   longer touches `PluginManager` at all.

### Why these shapes

- **`StreamAdapter` is 7 methods, all with live call sites** (deletion test).
  `getCurrentQuality` / `getQualities` / `name` were considered and rejected
  — no cross-seam caller. `recoverPlayback` stays on the adapter (it has no
  other home now that adapters aren't `PlayerPlugin`s); a separate
  `RecoveryAdapter` was rejected as a single-implementation hypothetical seam.
- **`StreamSink` is 4 methods replacing 8 reverse-driving points** (5 emit /
  register calls + the setQuality round-trip + emit('waiting')/('canplay')).
  `loadingStateChanged(boolean)` unifies the two-state loading machine rather
  than splitting `waiting()` / `canPlay()`.
- **`StreamContext` is 3 fields** (down from `PluginContext`'s ~20). The
  `videoElement` getter is lazy because the engine may attach the element
  after the adapter is constructed (matches today's timing — plugins read
  `context.videoElement` only inside `onSourceChange`).

## Alternatives considered

- **Just cache the adapter in the engine (form 2).** Would collapse the three
  duplicated dispatch sites but keep adapters as `PlayerPlugin`s still driven
  through the event bus. Rejected: the candidate's deletion test is only fully
  satisfied once the engine stops reaching for plugins by library name *and*
  adapters stop poking the engine through `emit`.
- **Full rewrite of the engine's state-machine drive model (form 3b + more).**
  Replacing all video-element→engine event wiring, not just adapter→engine.
  Explicitly **out of scope**: `<video>` element events driving the engine is
  legitimate (the engine owns the element); only adapter→engine reverse-driving
  is being removed.
- **Pull model for quality (engine queries `adapter.getQualities()`).** Rejected:
  HLS/DASH quality lists are produced asynchronously after manifest parse; the
  engine cannot poll. A "ready" signal is needed regardless, and once it exists
  it should carry the data (one round-trip beats two).
- **Merge quality resolution + change into one discriminated callback.**
  Rejected as a wider interface (callers switch on `kind`).

## Implementation plan (two PRs)

**PR1 — form 3a: adapters independent, keep event reverse-driving.**
Structural only, zero behavior change. Creates `StreamAdapter` / `StreamContext`,
moves the three plugins to independent adapter classes, has the engine
instantiate + cache `currentStreamAdapter`, rewrites the four dispatch sites to
read the cached adapter, removes stream plugins from `defaultPlugins.ts` and
from `PluginManager`. Adapters still drive the engine through the old
`emit` / `register*` calls (forwarded via `StreamContext`) — the sink is not
introduced yet. Validates candidate #1's deletion test in isolation.

**PR2 — form 3b: `StreamSink`, remove event reverse-driving.**
Introduces `StreamSink`, adds the `sink` parameter to `onSourceChange`,
rewrites the three adapters to deliver state through the four sink methods
instead of `emit` / `register*`, deletes the intercepted-`emit` hack in the
engine, moves default-quality decisioning into the engine's
`qualitiesResolved` handler. Adds the layer-1 contract test
(`FakeStreamAdapter`) that pins the no-round-trip semantics.

Splitting is required so PR1 (a pure structural refactor that can be
byte-compared) is reviewable and revertable independently of PR2 (a
control-flow change with real behavior risk).

## Consequences for future work

- A test fake for the player now exists as a concept (`FakeStreamAdapter`);
  player-engine logic that used to require a `<video>` element and a real
  library can now be unit-tested through the adapter interface.
- `PluginContext` remains for `SubtitlesPlugin` / `AnalyticsPlugin`. Narrowing
  it is a separate, future epic (not covered here).
- The engine's state machine still listens to `<video>` element events
  directly; redesigning that drive model is explicitly deferred.
