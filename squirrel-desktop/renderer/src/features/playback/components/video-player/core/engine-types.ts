/**
 * Player engine public types.
 *
 * Extracted from createPlayerEngine.ts so the engine's public surface
 * (PlayerEngineOptions / PlayerEngine) and its structural plugin controller
 * views can be imported without pulling the full engine factory.
 */

import type { EventEmitter } from './EventEmitter'
import type { IPlayerAdapter, UserConfig } from './PlayerAdapter'
import type { StreamAdapter } from './StreamAdapter'
import type { HlsAdapterOptions } from '../adapters/HlsAdapter'
import type { DashAdapterOptions } from '../adapters/DashAdapter'
import type { ShakaDashAdapterOptions } from '../adapters/ShakaDashAdapter'
import type {
  MediaSource,
  PlayerError,
  PlayerEvents,
  PlayerStats,
  PluginConfig,
  QualityLevel,
  QualitySelectionRequest,
  SubtitleStyle,
  SubtitleTrack,
} from './types'

// ponytail: structural views of player plugins the engine drives. Typed
// structurally (only the methods the engine actually calls) to avoid importing
// the concrete plugin classes, which would create a runtime cycle
// (plugins -> core).
export interface QualityController {
  setQuality?: (quality: unknown) => void
}

export interface SubtitleController {
  setTracks?: (tracks: SubtitleTrack[]) => Promise<void>
  loadTrack?: (track: SubtitleTrack) => boolean | Promise<boolean | void>
  enable?: () => void
  disable?: () => void
  toggle?: () => void
  exportStyle?: () => SubtitleStyle
  importStyle?: (style: SubtitleStyle) => void
  applyPreset?: (presetId: string) => void
  setSubtitleOffset?: (offsetSeconds: number) => void
  getSubtitleOffset?: () => number
}

export type PlayerEngineOptions = {
  autoplay?: boolean
  autoplayNext?: boolean
  muted?: boolean
  volume?: number
  loop?: boolean
  playbackRate?: number

  adapter?: IPlayerAdapter
  plugins?: PluginConfig[]

  onPlay?: () => void
  onPause?: () => void
  onEnded?: () => void
  onError?: (error: PlayerError) => void
  onTimeUpdate?: (time: number) => void
  onQualityChange?: (quality: string) => void

  errorRecovery?: {
    maxRetries?: number
    retryDelay?: number
    enableQualityFallback?: boolean
  }

  progress?: {
    saveInterval?: number
    thresholdSeconds?: number
  }

  /**
   * Stream adapter configuration (see docs/adr/0001). The engine instantiates
   * the HLS / dashjs / shaka adapters itself from this bag; they are no longer
   * registered as PlayerPlugins. Omitted entries fall back to the adapters'
   * built-in defaults, and a missing technology is simply not available.
   */
  streamAdapters?: StreamAdapterOptions
}

export type StreamAdapterOptions = {
  // ponytail: these are `import type`-only references to the adapter modules.
  // They stay type-level (no runtime cycle): the adapters import only types
  // from core/, and core/ imports only types from adapters/.
  hls?: HlsAdapterOptions
  dash?: DashAdapterOptions
  'shaka-dash'?: ShakaDashAdapterOptions
  /** When false, the HLS adapter is not instantiated even for .m3u8 sources. */
  enableHls?: boolean
  /** When false, neither DASH adapter is instantiated for .mpd sources. */
  enableDash?: boolean
}

export type PlayerEngine = {
  attachVideoElement: (el: HTMLVideoElement | null) => void
  attachContainerElement: (el: HTMLElement | null) => void

  init: () => Promise<void>
  destroy: () => void

  play: () => Promise<boolean>
  pause: () => void
  seek: (time: number) => void
  setVolume: (volume: number) => void
  setMuted: (muted: boolean) => void
  toggleMute: () => void
  setPlaybackRate: (rate: number) => void
  setLoop: (loop: boolean) => void
  setAutoplay: (autoplay: boolean) => void
  setAutoplayNext: (autoplayNext: boolean) => void

  setQuality: (quality: QualitySelectionRequest) => void

  toggleFullscreen: () => Promise<void>
  togglePictureInPicture: () => Promise<void>

  loadSource: (source: MediaSource) => void
  getSource: () => MediaSource | null
  getSourceType: () => 'native' | 'hls' | 'dash' | null

  setSubtitleTracks: (tracks: SubtitleTrack[]) => Promise<void>
  setSubtitle: (track: SubtitleTrack | null) => void
  toggleSubtitles: () => void
  getSubtitleStyle: () => SubtitleStyle
  setSubtitleStyle: (style: SubtitleStyle) => void
  applySubtitlePreset: (presetId: string) => void
  setSubtitleOffset: (offsetSeconds: number) => void
  getSubtitleOffset: () => number

  saveProgress: () => void
  loadProgress: (progressKey: string) => Promise<number | null>

  getConfig: () => UserConfig
  getQualities: () => QualityLevel[]
  getCurrentQualityLabel: () => string | null
  getCurrentQualityId: () => string | number | null
  getSubtitleTracks: () => SubtitleTrack[]
  getCurrentSubtitle: () => SubtitleTrack | null

  getPlugin: <T>(name: string) => T | null
  getStreamAdapter: () => StreamAdapter | null
  getStats: () => PlayerStats
  on: EventEmitter<PlayerEvents>['on']
  off: EventEmitter<PlayerEvents>['off']
}
