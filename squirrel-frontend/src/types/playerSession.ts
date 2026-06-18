import type { MediaSource, SubtitleTrack, IPlayerAdapter } from '@/components/video-player/core'
import type { ClipMarker, VideoPageVideo } from './videoPlayback'

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

export interface PlayerSessionState {
  active: boolean
  target: HTMLElement | null
  source: MediaSource | null
  subtitles: SubtitleTrack[]
  clipMarkers: ClipMarker[]
  title: string
  uploader: string
  initialTime: number
  hasPrev: boolean
  hasNext: boolean
  externalError: ExternalErrorState | null
  externalLoading: boolean
  adapter: IPlayerAdapter | null
  theme: string
  widescreen: boolean
  currentVideoId: string
  videoSnapshot: VideoPageVideo | null
  relatedVideos: VideoPageVideo[]
  loadingRelated: boolean
  pictureInPicture: boolean
  handlers: PlayerHandlers
  playlist: PlaylistEntry[]
  playlistIndex: number
}
