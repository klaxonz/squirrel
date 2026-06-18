/**
 * Player engine public types.
 *
 * Extracted from createPlayerEngine.ts so the engine's public surface
 * (PlayerEngineOptions / PlayerEngine) and its structural plugin controller
 * views can be imported without pulling the full engine factory.
 */

import type { EventEmitter } from './EventEmitter'
import type { IPlayerAdapter, UserConfig } from './PlayerAdapter'
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
  getStats: () => PlayerStats
  on: EventEmitter<PlayerEvents>['on']
  off: EventEmitter<PlayerEvents>['off']
}
