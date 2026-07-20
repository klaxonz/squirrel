import { describe, it, expect, vi } from 'vitest'
import { createErrorRecovery, detectSourceType } from './error-recovery'
import { EventEmitter } from './EventEmitter'
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
  const video = {
    paused: opts?.paused ?? false,
    ended: false,
    currentTime: 56,
    duration: 1700,
    addEventListener: vi.fn(),
  } as unknown as HTMLVideoElement

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
    logger: {
      debug: vi.fn(),
      info: vi.fn(),
      warn: vi.fn(),
      error: vi.fn(),
    } as any,
    adapter: {
      reportError: vi.fn(async () => {}),
    } as any,
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
