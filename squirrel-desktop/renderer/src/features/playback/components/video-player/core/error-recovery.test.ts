import { describe, it, expect, vi } from 'vitest'
import { createErrorRecovery, detectSourceType } from './error-recovery'
import { EventEmitter } from './EventEmitter'
import type { IPlayerAdapter } from './PlayerAdapter'
import type { PlayerLogger } from './logger'
import type { MediaSource, PlayerError, QualityLevel } from './types'

describe('detectSourceType', () => {
  it('classifies FreeTube-style data: dash MPD as dash', () => {
    expect(detectSourceType('data:application/dash+xml;charset=UTF-8,%3CMPD')).toBe('dash')
  })

  it('still classifies .mpd and m3u8 correctly', () => {
    expect(detectSourceType('https://cdn.example/manifest.mpd')).toBe('dash')
    expect(detectSourceType('https://cdn.example/playlist.m3u8')).toBe('hls')
    expect(detectSourceType('https://cdn.example/video.mp4')).toBe('native')
  })
})

function createHarness(opts?: {
  paused?: boolean
  playbackRate?: number
  readyState?: number
  bufferStart?: number
  bufferEnd?: number
  currentTime?: number
  qualities?: QualityLevel[]
  registeredQualityId?: string | number | null
  enableQualityFallback?: boolean
  maxRetries?: number
}) {
  const qualities = opts?.qualities ?? [
    { id: '1440', label: '1440p', height: 1440 },
    { id: '1080', label: '1080p', height: 1080 },
    { id: '720', label: '720p', height: 720 },
  ]
  let registeredQualityId: string | number | null = opts?.registeredQualityId ?? '1440'
  let retryCount = 0
  let loading = true
  const setQuality = vi.fn((q: string | number) => {
    registeredQualityId = q
  })
  const play = vi.fn(async () => true)
  const doLoadSource = vi.fn()
  const onError = vi.fn()
  const currentTime = opts?.currentTime ?? 56
  const bufferStart = opts?.bufferStart
  const bufferEnd = opts?.bufferEnd
  const buffered = (typeof bufferStart === 'number' && typeof bufferEnd === 'number')
    ? {
        length: 1,
        start: () => bufferStart,
        end: () => bufferEnd,
      }
    : { length: 0, start: () => 0, end: () => 0 }
  const video = {
    paused: opts?.paused ?? false,
    ended: false,
    currentTime,
    duration: 1700,
    playbackRate: opts?.playbackRate ?? 1,
    defaultPlaybackRate: 1,
    readyState: opts?.readyState ?? 0,
    buffered,
    addEventListener: vi.fn(),
  } as unknown as HTMLVideoElement
  const logger: PlayerLogger = {
    debug: vi.fn(),
    info: vi.fn(),
    warn: vi.fn(),
    error: vi.fn(),
  }
  const adapter: IPlayerAdapter = {
    loadConfig: vi.fn(async () => ({})),
    saveConfig: vi.fn(async () => {}),
    saveProgress: vi.fn(async () => {}),
    loadProgress: vi.fn(async () => null),
    getHistory: vi.fn(async () => []),
    clearHistory: vi.fn(async () => {}),
    reportError: vi.fn(async () => {}),
  }

  const recovery = createErrorRecovery({
    getVideoElement: () => video,
    getLoading: () => loading,
    setLoading: (v) => { loading = v },
    getRetryCount: () => retryCount,
    setRetryCount: (v) => { retryCount = v },
    getQualities: () => qualities,
    setQualities: () => {},
    getRegisteredQualityId: () => registeredQualityId,
    getCurrentSource: () => ({ src: 'blob:dash', type: 'dash', key: 'k1' }) as MediaSource,
    getCurrentSourceType: () => 'dash',
    getCurrentSourceKey: () => 'k1',
    setCurrentSourceKey: () => {},
    getPendingSourceKey: () => '',
    setPendingSourceKey: () => {},
    getAutoPlayOnReady: () => false,
    setAutoPlayOnReady: () => {},
    getProgressKey: () => 'vid-1',
    getMaxRetries: () => opts?.maxRetries ?? 3,
    getRetryDelay: () => 10,
    getEnableQualityFallback: () => opts?.enableQualityFallback ?? true,
    events: new EventEmitter(),
    getStreamAdapter: () => null,
    logger,
    adapter,
    onError,
    play,
    setQuality,
    doLoadSource,
  })

  return {
    recovery,
    setQuality,
    play,
    doLoadSource,
    video,
    getLoading: () => loading,
    getRetryCount: () => retryCount,
    getRegisteredQualityId: () => registeredQualityId,
  }
}

describe('error recovery stall handling', () => {
  it('retries at the same quality before stepping down on stall', async () => {
    const { recovery, setQuality, doLoadSource } = createHarness({
      paused: false,
      maxRetries: 3,
    })
    const err: PlayerError = {
      code: 'STALL_DETECTED',
      message: 'Playback stalled while waiting for media',
      fatal: false,
    }

    const recovered = await recovery.handleRecoveryError(err)

    expect(recovered).toBe(true)
    // Soft stall recovery must NOT full-reload the source (that rewinds the playhead).
    expect(setQuality).not.toHaveBeenCalled()
    expect(doLoadSource).not.toHaveBeenCalled()
  })

  it('falls back to a lower quality only after stall retries are exhausted', async () => {
    const { recovery, setQuality, getRegisteredQualityId } = createHarness({
      paused: false,
      maxRetries: 0,
    })
    const err: PlayerError = {
      code: 'STALL_DETECTED',
      message: 'Playback stalled while waiting for media',
      fatal: false,
    }

    const recovered = await recovery.handleRecoveryError(err)

    expect(recovered).toBe(true)
    expect(setQuality).toHaveBeenCalled()
    expect(String(getRegisteredQualityId())).toBe('1080')
  })

  it('resumes via play() when stall happens while paused', async () => {
    const { recovery, play, setQuality } = createHarness({ paused: true })
    const err: PlayerError = {
      code: 'STALL_DETECTED',
      message: 'Playback stalled while waiting for media',
      fatal: false,
    }

    const recovered = await recovery.handleRecoveryError(err)

    expect(recovered).toBe(true)
    expect(play).toHaveBeenCalled()
    expect(setQuality).not.toHaveBeenCalled()
  })

  it('restores rate=0 starve flag, plays, and clears loading when buffer is ahead', async () => {
    // Shaka PlayRateController leaves playbackRate=0 while STARVING; after
    // rebuffer the playhead has media but spinner/rate stick without this path.
    const { recovery, play, setQuality, video, getLoading } = createHarness({
      paused: false,
      playbackRate: 0,
      readyState: 2,
      currentTime: 56,
      bufferStart: 55.9,
      bufferEnd: 58,
    })
    const err: PlayerError = {
      code: 'STALL_DETECTED',
      message: 'Playback stalled while waiting for media',
      fatal: false,
    }

    const recovered = await recovery.handleRecoveryError(err)

    expect(recovered).toBe(true)
    expect(video.playbackRate).toBe(1)
    expect(play).toHaveBeenCalled()
    expect(getLoading()).toBe(false)
    expect(setQuality).not.toHaveBeenCalled()
  })

  it('does not escalate duplicate recovery to failure', async () => {
    const { recovery } = createHarness({ paused: false, maxRetries: 3 })
    const err: PlayerError = {
      code: 'STALL_DETECTED',
      message: 'Playback stalled while waiting for media',
      fatal: false,
    }

    // Concurrent stall while retry is in-flight must return true (suppress fatal).
    const first = recovery.handleRecoveryError(err)
    const second = await recovery.handleRecoveryError(err)
    const firstResult = await first

    expect(firstResult).toBe(true)
    expect(second).toBe(true)
  })
})
