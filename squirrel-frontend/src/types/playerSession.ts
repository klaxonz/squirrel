import type { MediaSource, SubtitleTrack } from '@/components/video-player/core'
import type { ClipMarker } from './videoPlayback'

export type ExternalErrorState = {
  code: string
  title: string
  message: string
  canRetry: boolean
}

// Structural handle for the global VideoPlayer component instance exposed via
// the player store. Typed structurally to avoid a circular import on the SFC.
export interface VideoPlayerHandle {
  $el?: HTMLElement
  seek?: (time: number) => void
  play?: () => Promise<void>
}

// Payload VideoPlayer emits on `ended` — reflects the active user settings so
// handlers can decide autoplay-next / loop behaviour.
export type VideoEndedEvent = {
  autoplay?: boolean
  autoplayNext?: boolean
  loop?: boolean
}

export type PlayerHandlers = {
  onPlay?: (() => void) | null
  onPause?: (() => void) | null
  onEnded?: ((event?: VideoEndedEvent) => void | Promise<void>) | null
  onTimeUpdate?: ((currentTime: number) => void) | null
  onPrev?: (() => void | Promise<void>) | null
  onNext?: (() => void | Promise<void>) | null
  onRetry?: (() => void | Promise<void>) | null
  onWidescreenChange?: ((enabled: boolean) => void) | null
  onClipMarkerSelect?: ((time: number) => void | Promise<void>) | null
  onClipMarkersUpdated?: ((markers: ClipMarker[]) => void) | null
}

export interface PlaylistEntry {
  id: string
  title: string
  thumbnail?: string
  source: MediaSource | null
  subtitles?: SubtitleTrack[]
  clipMarkers?: ClipMarker[]
  videoId?: string | number
  duration?: number
}

// ponytail: ADR-0002 — the 22-field PlayerSessionState interface used to live
// here and was the shape of `playerStore.session`. It moved (renamed to
// PlaybackSessionFacts, with `currentVideoId`→`videoId` and
// `videoSnapshot`→`video`) to `composables/usePlaybackSession.ts`. `active` /
// `target` / `adapter` / `handlers` were never facts — they are wiring state
// now on the slimmed Pinia store (`stores/player.ts`), passed alongside facts
// via the facade's PlayerSessionPayload.

