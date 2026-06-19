import { reactive, readonly } from 'vue'

import type { MediaSource, SubtitleTrack } from '@/features/playback/components/video-player/core'
import type { ExternalErrorState, PlaylistEntry } from '@/features/playback/types/playerSession'
import type { ClipMarker, VideoPageVideo } from '@/features/playback/types/videoPlayback'

/**
 * The facts-layer state for "what is playing right now".
 *
 * See ADR-0002. This is the single owner of session facts (which video, its
 * source, its metadata, its related/playlist context, whether it is in PiP).
 * The runtime layer (playback progress, volume, buffering — owned by the
 * engine + runtime/PlayerStore.ts) is deliberately separate; the two layers
 * meet only through `initialTime` (facts → runtime, on session begin) and the
 * PiP fact (runtime → facts, via the engine event).
 */
export interface PlaybackSessionFacts {
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
  pictureInPicture: boolean
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

export interface PlaybackSession {
  /**
   * Read-only view of the session facts. Mutation goes through the verbs.
   *
   * Typed shallow-readonly so consumers can pass `facts.source` into props
   * that expect the mutable `MediaSource` type (Vue's runtime `readonly()`
   * wraps deeply; the shallow type annotation avoids `DeepReadonly`
   * incompatibilities on shared library types like `MediaSource.qualities`).
   * Runtime enforcement is still full-depth — `isReadonly(facts)` is true and
   * direct writes no-op.
   */
  readonly facts: Readonly<PlaybackSessionFacts>
  /** Switch to a different video: clear stale facts, mark loading. */
  beginNewVideo(videoId: string, seed?: VideoPageVideo | null): void
  /** Apply a partial patch to the facts. Unmentioned fields are left intact. */
  update(patch: Partial<PlaybackSessionFacts>): void
  /** Is this session already representing this video with complete facts? */
  isReusableFor(videoId: string): boolean
  /** View unmount: keep the session if PiP is active, clear otherwise. */
  release(): void
  /** Update the PiP fact. Engine events are the only legitimate writer. */
  setPictureInPicture(value: boolean): void
}

const createInitialFacts = (): PlaybackSessionFacts => ({
  videoId: '',
  source: null,
  video: null,
  subtitles: [],
  clipMarkers: [],
  initialTime: 0,
  externalError: null,
  externalLoading: false,
  relatedVideos: [],
  loadingRelated: false,
  pictureInPicture: false,
  title: '',
  uploader: '',
  theme: 'dark',
  widescreen: false,
  hasPrev: false,
  hasNext: false,
  playlist: [],
  playlistIndex: -1,
})

/**
 * App-scoped singleton. Lives for the lifetime of the app (mounted via
 * GlobalVideoPlayerHost); not persisted to storage — a refresh rebuilds the
 * session, by design. There is no `snapshot()` / `restore()` pair: the session
 * does not unmount, so nothing needs to be serialized across a view unmount.
 *
 * The singleton is module-scoped so every caller (`GlobalVideoPlayerHost`,
 * `useVideoPlaybackShell`, `useGlobalVideoPlayer`) shares one instance — the
 * facts-layer analogue of how `usePlayerStore` used to be the one Pinia store.
 */
let sessionInstance: PlaybackSession | null = null

const createSession = (): PlaybackSession => {
  const facts = reactive<PlaybackSessionFacts>(createInitialFacts())

  const beginNewVideo = (videoId: string, seed: VideoPageVideo | null = null): void => {
    // Only the session-ROOT facts are reset here — the ones that drive loading
    // state and reuse decisions. Presentation projections (title / uploader /
    // theme / widescreen / hasPrev / hasNext / playlist / initialTime) are
    // intentionally left untouched: in PR1 the shell's watcher re-fires on the
    // next tick with the new video's values and overwrites them, and clearing
    // them here would flash empty values in between. (PR2, once the watcher is
    // gone, will have the orchestrator call update() with the full new
    // presentation set right after beginNewVideo.)
    facts.videoId = String(videoId || '')
    facts.source = null
    facts.video = seed
    facts.externalError = null
    facts.externalLoading = true
    facts.relatedVideos = []
    facts.loadingRelated = false
    facts.subtitles = []
  }

  const update = (patch: Partial<PlaybackSessionFacts>): void => {
    Object.assign(facts, patch)
  }

  const isReusableFor = (videoId: string): boolean => {
    if (String(facts.videoId || '') !== String(videoId || '')) return false
    if (needsJavdbRefresh()) return false
    return !!(facts.source || facts.externalError || facts.externalLoading)
  }

  // Mirrors the old shouldRefreshJavdbSession() shell helper: a javdb video
  // whose actors are unresolved is treated as incomplete and forces a refresh.
  const needsJavdbRefresh = (): boolean => {
    const url = String(facts.video?.url || '')
    if (!url.includes('javdb.com/')) return false
    const actors = facts.video?.actors
    return !Array.isArray(actors) || !actors.some((actor) => String(actor?.name || '').trim())
  }

  const release = (): void => {
    // PiP continuity: if the session is in picture-in-picture, the view can
    // unmount while playback keeps going in the PiP window. Keep the facts so
    // the next view mount can reuse this session. Otherwise the session is
    // done — clear it so a stale video doesn't leak into the next mount.
    if (facts.pictureInPicture) return
    Object.assign(facts, createInitialFacts())
  }

  const setPictureInPicture = (value: boolean): void => {
    facts.pictureInPicture = value
  }

  return {
    // Cast to the shallow Readonly<Facts> so callers can pass `facts.source`
    // into props expecting the mutable `MediaSource` type. Runtime enforcement
    // is still Vue's full-depth readonly() — see the `facts is readonly` test.
    facts: readonly(facts) as unknown as Readonly<PlaybackSessionFacts>,
    beginNewVideo,
    update,
    isReusableFor,
    release,
    setPictureInPicture,
  }
}

/** Access the app-scoped PlaybackSession singleton (creating it on first call). */
export function usePlaybackSession(): PlaybackSession {
  if (!sessionInstance) sessionInstance = createSession()
  return sessionInstance
}

/**
 * Test-only escape hatch: drop the cached singleton so the next
 * `usePlaybackSession()` call builds a fresh session. The contract test suite
 * needs an isolated session per case; production code never resets.
 */
export function __resetPlaybackSessionForTests(): void {
  sessionInstance = null
}
