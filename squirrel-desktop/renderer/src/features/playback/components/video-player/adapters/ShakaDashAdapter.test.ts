import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import type { StreamContext } from '../core/StreamAdapter'
import type { StreamSink } from '../core/StreamSink'
import type { PlayerError, PlayerState } from '../core/types'

const shakaMockState = vi.hoisted(() => {
  const lowTrack = {
    id: 278,
    type: 'variant',
    active: true,
    width: 256,
    height: 144,
    bandwidth: 100_000,
    videoCodec: 'vp9',
  }
  const midTrack = {
    id: 247,
    type: 'variant',
    active: false,
    width: 1280,
    height: 720,
    bandwidth: 1_900_000,
    videoCodec: 'vp9',
  }
  const highTrack = {
    id: 248,
    type: 'variant',
    active: false,
    width: 1920,
    height: 1080,
    bandwidth: 3_400_000,
    videoCodec: 'vp9',
  }
  return {
    latestPlayer: null as unknown,
    audioTracks: [] as Array<Record<string, unknown>>,
    loadFailures: 0,
    lowTrack,
    midTrack,
    highTrack,
    variantTracks: [lowTrack, midTrack, highTrack] as Array<Record<string, unknown>>,
  }
})

const sabrMockState = vi.hoisted(() => ({
  latestAdapter: null as unknown,
}))

vi.mock('googlevideo/sabr-streaming-adapter', () => {
  class MockSabrStreamingAdapter {
    attach = vi.fn()
    dispose = vi.fn()
    onMintPoToken = vi.fn()
    onReloadPlayerResponse = vi.fn()
    onSnackbarMessage = vi.fn()
    setStreamingURL = vi.fn()
    setUstreamerConfig = vi.fn()
    setServerAbrFormats = vi.fn()

    constructor() {
      sabrMockState.latestAdapter = this
    }
  }

  return { SabrStreamingAdapter: MockSabrStreamingAdapter }
})

vi.mock('shaka-player', () => {
  const networkingEngine = {
    registerRequestFilter: vi.fn(),
    registerResponseFilter: vi.fn(),
    unregisterRequestFilter: vi.fn(),
    unregisterResponseFilter: vi.fn(),
    request: vi.fn(),
  }

  class MockPlayer {
    attach = vi.fn(async () => {})
    configure = vi.fn()
    load = vi.fn(async () => {
      if (shakaMockState.loadFailures > 0) {
        shakaMockState.loadFailures -= 1
        throw new Error('mock SABR load failure')
      }
    })
    destroy = vi.fn(async () => {})
    addEventListener = vi.fn()
    getVariantTracks = vi.fn(() => shakaMockState.variantTracks)
    getAudioTracks = vi.fn(() => shakaMockState.audioTracks)
    getNetworkingEngine = vi.fn(() => networkingEngine)
    getConfiguration = vi.fn(() => ({
      abr: { enabled: true },
      streaming: { retryParameters: {} },
    }))
    isBuffering = vi.fn(() => false)
    selectVariantTrack = vi.fn()
    selectAudioTrack = vi.fn()
    retryStreaming = vi.fn(() => true)

    constructor() {
      shakaMockState.latestPlayer = this
    }
  }

  return {
    default: {
      Player: MockPlayer,
      polyfill: { installAll: vi.fn() },
      net: {
        NetworkingEngine: {
          RequestType: { SEGMENT: 1 },
          makeRequest: vi.fn(),
        },
      },
      util: {
        StringUtils: { fromUTF8: vi.fn(() => '') },
      },
    },
  }
})

import { ShakaDashAdapter } from './ShakaDashAdapter'
import { SabrShakaPlayerAdapter } from './SabrShakaPlayerAdapter'

interface MockShakaPlayer {
  configure: ReturnType<typeof vi.fn>
  load: ReturnType<typeof vi.fn>
  selectAudioTrack: ReturnType<typeof vi.fn>
  selectVariantTrack: ReturnType<typeof vi.fn>
  retryStreaming: ReturnType<typeof vi.fn>
}

const flushPromises = async (): Promise<void> => {
  for (let index = 0; index < 8; index += 1) {
    await Promise.resolve()
  }
}

describe('ShakaDashAdapter post-seek video recovery', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    vi.stubGlobal('window', globalThis)
    shakaMockState.latestPlayer = null
    shakaMockState.audioTracks = []
    shakaMockState.loadFailures = 0
    // Default ladder: 144p active (cold ABR case).
    shakaMockState.lowTrack.active = true
    shakaMockState.midTrack.active = false
    shakaMockState.highTrack.active = false
    shakaMockState.variantTracks = [
      shakaMockState.lowTrack,
      shakaMockState.midTrack,
      shakaMockState.highTrack,
    ]
    sabrMockState.latestAdapter = null
  })

  afterEach(() => {
    vi.unstubAllGlobals()
    vi.useRealTimers()
  })

  it('rebuilds the active variant, then reloads at the live audio playhead when video frames stay frozen', async () => {
    let frameCallbackId = 0
    const frameCallbacks: { latest: VideoFrameRequestCallback | null } = { latest: null }
    const video = {
      currentTime: 0,
      paused: false,
      ended: false,
      playbackRate: 1,
      defaultPlaybackRate: 1,
      getVideoPlaybackQuality: vi.fn(() => ({ totalVideoFrames: 10 })),
      requestVideoFrameCallback: vi.fn((callback: VideoFrameRequestCallback) => {
        frameCallbackId += 1
        frameCallbacks.latest = callback
        return frameCallbackId
      }),
      cancelVideoFrameCallback: vi.fn(),
      play: vi.fn(async () => {}),
    } as unknown as HTMLVideoElement
    const context: StreamContext = {
      videoElement: () => video,
      getState: () => ({ quality: null } as PlayerState),
      logger: {
        debug: vi.fn(),
        info: vi.fn(),
        warn: vi.fn(),
        error: vi.fn(),
      },
    }
    const sink: StreamSink = {
      qualitiesResolved: vi.fn(),
      qualityChanged: vi.fn(),
      loadingStateChanged: vi.fn(),
      error: vi.fn(),
    }
    const adapter = new ShakaDashAdapter(context)
    const source = 'data:application/dash+xml;charset=UTF-8,%3CMPD%3E'

    adapter.onSourceChange({ src: source, type: 'dash', playbackEngine: 'shaka' }, sink)
    await flushPromises()
    const player = shakaMockState.latestPlayer as MockShakaPlayer
    expect(player.load).toHaveBeenCalledWith(source, null, 'application/dash+xml')

    let seekCompleted = false
    const seekCompletion = adapter.seek(100).then(() => { seekCompleted = true })
    video.currentTime = 102
    await vi.advanceTimersByTimeAsync(3000)

    expect(player.selectVariantTrack).toHaveBeenCalledWith(
      expect.objectContaining({ id: 278, active: true }),
      true,
      0,
    )
    expect(player.retryStreaming).toHaveBeenCalledWith(0.1)
    expect(seekCompleted).toBe(false)

    video.currentTime = 104
    await vi.advanceTimersByTimeAsync(3000)
    await flushPromises()

    expect(player.load).toHaveBeenLastCalledWith(source, 104, 'application/dash+xml')
    expect(video.play).toHaveBeenCalled()
    expect(seekCompleted).toBe(false)

    video.currentTime = 104.5
    frameCallbacks.latest?.(performance.now(), { mediaTime: 104.5 } as VideoFrameCallbackMetadata)
    await flushPromises()
    await seekCompletion
    expect(seekCompleted).toBe(true)
    expect(sink.error).not.toHaveBeenCalled()
    adapter.destroy()
  })

  it('selects creator-original audio instead of a localized dub or Stable Volume mix', async () => {
    const video = {
      currentTime: 0,
      paused: true,
      ended: false,
      playbackRate: 1,
      defaultPlaybackRate: 1,
    } as HTMLVideoElement
    const context: StreamContext = {
      videoElement: () => video,
      getState: () => ({ quality: null } as PlayerState),
      logger: {
        debug: vi.fn(),
        info: vi.fn(),
        warn: vi.fn(),
        error: vi.fn(),
      },
    }
    const sink: StreamSink = {
      qualitiesResolved: vi.fn(),
      qualityChanged: vi.fn(),
      loadingStateChanged: vi.fn(),
      error: vi.fn(),
    }
    const dubbed = {
      active: true,
      language: 'ar',
      label: 'Arabic',
      primary: false,
      roles: ['alternate', 'dub'],
      codecs: 'opus',
      mimeType: 'audio/webm',
    }
    const stableVolume = {
      active: false,
      language: 'en-US',
      label: 'English (US) original (Stable Volume)',
      primary: true,
      roles: ['main', 'enhanced-audio-intelligibility'],
      codecs: 'opus',
      mimeType: 'audio/webm',
    }
    const original = {
      active: false,
      language: 'en-US',
      label: 'English (US) original',
      primary: true,
      roles: ['main'],
      codecs: 'opus',
      mimeType: 'audio/webm',
    }
    shakaMockState.audioTracks = [dubbed, stableVolume, original]

    const adapter = new ShakaDashAdapter(context)
    adapter.onSourceChange({
      src: 'data:application/dash+xml;charset=UTF-8,%3CMPD%3E',
      type: 'dash',
      playbackEngine: 'shaka',
    }, sink)
    await flushPromises()

    const player = shakaMockState.latestPlayer as MockShakaPlayer
    expect(player.configure).toHaveBeenCalledWith(expect.objectContaining({
      preferredAudio: [expect.objectContaining({ role: 'main' })],
    }))
    expect(player.selectAudioTrack).toHaveBeenCalledWith(original, 0)
    expect(player.selectAudioTrack).not.toHaveBeenCalledWith(dubbed, expect.anything())
    expect(player.selectAudioTrack).not.toHaveBeenCalledWith(stableVolume, expect.anything())
    expect(context.logger.info).toHaveBeenCalledWith(
      '[ShakaDashAdapter] Selected creator-original audio track',
      expect.objectContaining({ language: 'en-US' }),
    )
    adapter.destroy()
  })

  it('pins 1080p startup quality without disabling ABR', async () => {
    const video = {
      currentTime: 0,
      paused: true,
      ended: false,
      playbackRate: 1,
      defaultPlaybackRate: 1,
    } as HTMLVideoElement
    const context: StreamContext = {
      videoElement: () => video,
      getState: () => ({ quality: null } as PlayerState),
      logger: {
        debug: vi.fn(),
        info: vi.fn(),
        warn: vi.fn(),
        error: vi.fn(),
      },
    }
    const sink: StreamSink = {
      qualitiesResolved: vi.fn(),
      qualityChanged: vi.fn(),
      loadingStateChanged: vi.fn(),
      error: vi.fn(),
    }

    const adapter = new ShakaDashAdapter(context)
    adapter.onSourceChange({
      src: 'data:application/dash+xml;charset=UTF-8,%3CMPD%3E',
      type: 'dash',
      playbackEngine: 'shaka',
    }, sink)
    await flushPromises()

    const player = shakaMockState.latestPlayer as MockShakaPlayer
    // Load starts with ABR off so a warm bandwidth estimate cannot fetch
    // 4K before the pin; defaultBandwidthEstimate still seeds ~1080p.
    expect(player.configure).toHaveBeenCalledWith(expect.objectContaining({
      abr: expect.objectContaining({
        enabled: false,
        defaultBandwidthEstimate: 6_000_000,
      }),
    }))
    // Opening track was 144p; pin the 1080p rung (official-style start) without
    // clearing buffer.
    expect(player.selectVariantTrack).toHaveBeenCalledWith(
      expect.objectContaining({ id: 248, height: 1080 }),
      false,
      0,
    )
    // ABR re-enabled after the pin so quality can still climb.
    expect(player.configure).toHaveBeenCalledWith({ abr: { enabled: true } })
    adapter.destroy()
  })

  it('keeps a warm 1080p active track at the startup rung before first media', async () => {
    // Warm ABR case: prior throughput left 1080p as the active opening track —
    // already the startup target, so no downshift and no buffer clear.
    shakaMockState.lowTrack.active = false
    shakaMockState.midTrack.active = false
    shakaMockState.highTrack.active = true
    shakaMockState.variantTracks = [
      shakaMockState.highTrack,
      shakaMockState.midTrack,
      shakaMockState.lowTrack,
    ]

    const video = {
      currentTime: 0,
      paused: true,
      ended: false,
      playbackRate: 1,
      defaultPlaybackRate: 1,
    } as HTMLVideoElement
    const context: StreamContext = {
      videoElement: () => video,
      getState: () => ({ quality: null } as PlayerState),
      logger: {
        debug: vi.fn(),
        info: vi.fn(),
        warn: vi.fn(),
        error: vi.fn(),
      },
    }
    const sink: StreamSink = {
      qualitiesResolved: vi.fn(),
      qualityChanged: vi.fn(),
      loadingStateChanged: vi.fn(),
      error: vi.fn(),
    }

    const adapter = new ShakaDashAdapter(context)
    adapter.onSourceChange({
      src: 'data:application/dash+xml;charset=UTF-8,%3CMPD%3E',
      type: 'dash',
      playbackEngine: 'shaka',
    }, sink)
    await flushPromises()

    const player = shakaMockState.latestPlayer as MockShakaPlayer
    // 1080p is already active and is the startup target — pin is a no-op,
    // buffer kept, ABR still re-enabled after load.
    expect(player.selectVariantTrack).not.toHaveBeenCalledWith(
      expect.objectContaining({ id: 247, height: 720 }),
      true,
      0,
    )
    expect(player.configure).toHaveBeenCalledWith({ abr: { enabled: true } })
    adapter.destroy()
  })

  it('falls back to the bundled DASH manifest when SABR cannot start', async () => {
    const video = {
      currentTime: 0,
      paused: true,
      ended: false,
      playbackRate: 1,
      defaultPlaybackRate: 1,
    } as HTMLVideoElement
    const context: StreamContext = {
      videoElement: () => video,
      getState: () => ({ quality: null } as PlayerState),
      logger: {
        debug: vi.fn(),
        info: vi.fn(),
        warn: vi.fn(),
        error: vi.fn(),
      },
    }
    const sink: StreamSink = {
      qualitiesResolved: vi.fn(),
      qualityChanged: vi.fn(),
      loadingStateChanged: vi.fn(),
      error: vi.fn(),
    }
    const sabrSource = 'data:application/dash+xml;charset=UTF-8,SABR'
    const fallbackSource = 'data:application/dash+xml;charset=UTF-8,DASH'
    shakaMockState.loadFailures = 1

    const adapter = new ShakaDashAdapter(context)
    adapter.onSourceChange({
      src: sabrSource,
      type: 'dash',
      playbackEngine: 'shaka',
      sabr: {
        serverAbrUrl: 'https://example.googlevideo.com/videoplayback?sabr=1',
        ustreamerConfig: 'dGVzdA==',
        formats: [{
          itag: 137,
          lastModified: '1',
          bitrate: 2_000_000,
          approxDurationMs: 60_000,
          width: 1920,
          height: 1080,
        }],
        clientInfo: {
          clientName: 1,
          clientVersion: '1.0',
          osName: 'Windows',
          osVersion: '10',
        },
        poToken: 'token',
        fallbackSrc: fallbackSource,
      },
    }, sink)
    await flushPromises()

    const player = shakaMockState.latestPlayer as MockShakaPlayer
    expect(player.load).toHaveBeenNthCalledWith(1, sabrSource, null, 'application/dash+xml')
    expect(player.load).toHaveBeenNthCalledWith(2, fallbackSource, null, 'application/dash+xml')
    expect(context.logger.warn).toHaveBeenCalledWith(
      '[ShakaDashAdapter] SABR load failed; falling back to DASH',
      expect.any(Error),
    )
    const sabrAdapter = sabrMockState.latestAdapter as {
      attach: ReturnType<typeof vi.fn>
      dispose: ReturnType<typeof vi.fn>
      setStreamingURL: ReturnType<typeof vi.fn>
    }
    expect(sabrAdapter.attach).toHaveBeenCalledWith(player)
    expect(sabrAdapter.setStreamingURL).toHaveBeenCalled()
    expect(sabrAdapter.dispose).toHaveBeenCalled()
    expect(sink.error).not.toHaveBeenCalled()
    adapter.destroy()
  })

  it('limits SABR media concurrency so YouTube does not impose startup backoff', async () => {
    const transport = new SabrShakaPlayerAdapter() as unknown as {
      acquireNetworkSlot: () => Promise<() => void>
    }
    const releaseFirst = await transport.acquireNetworkSlot()
    const releaseSecond = await transport.acquireNetworkSlot()
    let thirdAcquired = false
    const thirdSlot = transport.acquireNetworkSlot().then((release) => {
      thirdAcquired = true
      return release
    })

    await Promise.resolve()
    expect(thirdAcquired).toBe(false)

    releaseFirst()
    const releaseThird = await thirdSlot
    expect(thirdAcquired).toBe(true)

    releaseSecond()
    releaseThird()
  })

  it('refreshes the SABR session, then degrades to bundled DASH on a seek-triggered HTTP 4xx', async () => {
    const video = {
      currentTime: 0,
      paused: false,
      ended: false,
      playbackRate: 1,
      defaultPlaybackRate: 1,
      play: vi.fn(async () => {}),
    } as unknown as HTMLVideoElement
    const context: StreamContext = {
      videoElement: () => video,
      getState: () => ({ quality: null } as PlayerState),
      logger: {
        debug: vi.fn(),
        info: vi.fn(),
        warn: vi.fn(),
        error: vi.fn(),
      },
    }
    const sink: StreamSink = {
      qualitiesResolved: vi.fn(),
      qualityChanged: vi.fn(),
      loadingStateChanged: vi.fn(),
      error: vi.fn(),
    }
    const sabrSource = 'data:application/dash+xml;charset=UTF-8,SABR'
    const fallbackSource = 'data:application/dash+xml;charset=UTF-8,DASH'
    const refreshedSession = {
      serverAbrUrl: 'https://example.googlevideo.com/videoplayback?sabr=2',
      ustreamerConfig: 'cmVmcmVzaGVk',
      formats: [{
        itag: 137,
        lastModified: '2',
        bitrate: 2_000_000,
        approxDurationMs: 60_000,
        width: 1920,
        height: 1080,
      }],
      clientInfo: {
        clientName: 1,
        clientVersion: '1.0',
        osName: 'Windows',
        osVersion: '10',
      },
      poToken: 'refreshed-token',
    }
    const refresh = vi.fn(async () => refreshedSession)
    const sabrConfig = {
      serverAbrUrl: 'https://example.googlevideo.com/videoplayback?sabr=1',
      ustreamerConfig: 'dGVzdA==',
      formats: [{
        itag: 137,
        lastModified: '1',
        bitrate: 2_000_000,
        approxDurationMs: 60_000,
        width: 1920,
        height: 1080,
      }],
      clientInfo: {
        clientName: 1,
        clientVersion: '1.0',
        osName: 'Windows',
        osVersion: '10',
      },
      poToken: 'token',
      fallbackSrc: fallbackSource,
      refresh,
    }
    const source = {
      src: sabrSource,
      type: 'dash' as const,
      playbackEngine: 'shaka' as const,
      sabr: sabrConfig,
    }

    const adapter = new ShakaDashAdapter(context)
    adapter.onSourceChange(source, sink)
    await flushPromises()
    const player = shakaMockState.latestPlayer as MockShakaPlayer
    expect(player.load).toHaveBeenNthCalledWith(1, sabrSource, null, 'application/dash+xml')

    // Seek now so the recovery window is open.
    void adapter.seek(120)
    const err: PlayerError = {
      code: 'SHAKA_1008',
      message: 'Bad HTTP status code: 400',
      fatal: false,
      details: { data: ['https://googlevideo.example/seg', 400, {}, 1, 'https://googlevideo.example/seg'] },
    }
    const contextPayload = {
      retryCount: 0,
      maxRetries: 3,
      retryDelay: 10,
      source,
      currentTime: 123,
      wasPlaying: true,
    }

    // Attempt 1: refresh the SABR session and nudge the pipeline, no manifest reload.
    const firstAction = await adapter.handleProviderRecovery(err, contextPayload)
    expect(firstAction).toBe('handled')
    expect(refresh).toHaveBeenCalledTimes(1)
    expect(player.retryStreaming).toHaveBeenCalledWith(0.1)
    expect(player.load).not.toHaveBeenCalledWith(fallbackSource, expect.anything(), 'application/dash+xml')
    const sabrAdapter = sabrMockState.latestAdapter as {
      setStreamingURL: ReturnType<typeof vi.fn>
      dispose: ReturnType<typeof vi.fn>
    }
    expect(sabrAdapter.setStreamingURL).toHaveBeenLastCalledWith(refreshedSession.serverAbrUrl)

    // Attempt 2 (4xx recurs): degrade to bundled DASH at the seek target.
    const secondAction = await adapter.handleProviderRecovery(err, contextPayload)
    expect(secondAction).toBe('handled')
    expect(player.load).toHaveBeenNthCalledWith(2, fallbackSource, 123, 'application/dash+xml')
    expect(video.play).toHaveBeenCalled()

    // Already degraded — subsequent 4xx must NOT re-degrade or re-refresh.
    refresh.mockClear()
    const thirdAction = await adapter.handleProviderRecovery(err, contextPayload)
    expect(thirdAction).toBeNull()
    expect(refresh).not.toHaveBeenCalled()
    adapter.destroy()
  })

  it('leaves non-seek and non-4xx errors to the generic chain', async () => {
    const video = {
      currentTime: 0,
      paused: false,
      ended: false,
      playbackRate: 1,
      defaultPlaybackRate: 1,
    } as unknown as HTMLVideoElement
    const context: StreamContext = {
      videoElement: () => video,
      getState: () => ({ quality: null } as PlayerState),
      logger: {
        debug: vi.fn(),
        info: vi.fn(),
        warn: vi.fn(),
        error: vi.fn(),
      },
    }
    const sink: StreamSink = {
      qualitiesResolved: vi.fn(),
      qualityChanged: vi.fn(),
      loadingStateChanged: vi.fn(),
      error: vi.fn(),
    }
    const adapter = new ShakaDashAdapter(context)
    adapter.onSourceChange({
      src: 'data:application/dash+xml;charset=UTF-8,SABR',
      type: 'dash',
      playbackEngine: 'shaka',
      sabr: {
        serverAbrUrl: 'https://example.googlevideo.com/videoplayback?sabr=1',
        ustreamerConfig: 'dGVzdA==',
        formats: [],
        clientInfo: { clientName: 1, clientVersion: '1.0', osName: 'Windows', osVersion: '10' },
        poToken: 'token',
        fallbackSrc: 'data:application/dash+xml;charset=UTF-8,DASH',
      },
    }, sink)
    await flushPromises()

    // No seek happened: lastSeekAt = 0 → the 4xx must NOT be intercepted.
    const noSeek = await adapter.handleProviderRecovery({
      code: 'SHAKA_1008',
      message: 'Bad HTTP status code: 400',
      fatal: false,
      details: { data: ['https://googlevideo.example/seg', 400, {}, 1, 'https://googlevideo.example/seg'] },
    }, {
      retryCount: 0,
      maxRetries: 3,
      retryDelay: 10,
      source: null,
      currentTime: 0,
      wasPlaying: true,
    })
    expect(noSeek).toBeNull()

    // Seek happened, but the error is a plain abort (no HTTP status) — not a 4xx.
    void adapter.seek(120)
    const aborted = await adapter.handleProviderRecovery({
      code: 'SHAKA_1009',
      message: 'The operation was aborted',
      fatal: false,
      details: { data: ['OPERATION_ABORTED'] },
    }, {
      retryCount: 0,
      maxRetries: 3,
      retryDelay: 10,
      source: null,
      currentTime: 120,
      wasPlaying: true,
    })
    expect(aborted).toBeNull()
    adapter.destroy()
  })

  it('refreshes the SABR session on a mid-play empty UMP response (no seek), then degrades to DASH', async () => {
    const video = {
      currentTime: 0,
      paused: false,
      ended: false,
      playbackRate: 1,
      defaultPlaybackRate: 1,
      play: vi.fn(async () => {}),
    } as unknown as HTMLVideoElement
    const context: StreamContext = {
      videoElement: () => video,
      getState: () => ({ quality: null } as PlayerState),
      logger: {
        debug: vi.fn(),
        info: vi.fn(),
        warn: vi.fn(),
        error: vi.fn(),
      },
    }
    const sink: StreamSink = {
      qualitiesResolved: vi.fn(),
      qualityChanged: vi.fn(),
      loadingStateChanged: vi.fn(),
      error: vi.fn(),
    }
    const sabrSource = 'data:application/dash+xml;charset=UTF-8,SABR'
    const fallbackSource = 'data:application/dash+xml;charset=UTF-8,DASH'
    const refreshedSession = {
      serverAbrUrl: 'https://example.googlevideo.com/videoplayback?sabr=2',
      ustreamerConfig: 'cmVmcmVzaGVk',
      formats: [{
        itag: 137,
        lastModified: '2',
        bitrate: 2_000_000,
        approxDurationMs: 60_000,
        width: 1920,
        height: 1080,
      }],
      clientInfo: {
        clientName: 1,
        clientVersion: '1.0',
        osName: 'Windows',
        osVersion: '10',
      },
      poToken: 'refreshed-token',
    }
    const refresh = vi.fn(async () => refreshedSession)
    const sabrConfig = {
      serverAbrUrl: 'https://example.googlevideo.com/videoplayback?sabr=1',
      ustreamerConfig: 'dGVzdA==',
      formats: [{
        itag: 137,
        lastModified: '1',
        bitrate: 2_000_000,
        approxDurationMs: 60_000,
        width: 1920,
        height: 1080,
      }],
      clientInfo: {
        clientName: 1,
        clientVersion: '1.0',
        osName: 'Windows',
        osVersion: '10',
      },
      poToken: 'token',
      fallbackSrc: fallbackSource,
      refresh,
    }
    const source = {
      src: sabrSource,
      type: 'dash' as const,
      playbackEngine: 'shaka' as const,
      sabr: sabrConfig,
    }

    const adapter = new ShakaDashAdapter(context)
    adapter.onSourceChange(source, sink)
    await flushPromises()
    const player = shakaMockState.latestPlayer as MockShakaPlayer

    // Mid-play SABR invalidation: empty UMP response (Shaka 1002) WITHOUT any
    // preceding seek. The old generic chain classified this as a network
    // failure and stepped quality down 1080p→720p→480p; it must instead
    // refresh the session first (keeps the current rung), then degrade to the
    // bundled DASH ladder at the live playhead.
    const err: PlayerError = {
      code: 'SHAKA_1002',
      message: 'Empty SABR response without redirect information',
      fatal: false,
      details: { data: ['Empty SABR response without redirect information', { format: { itag: 251 } }] },
    }
    const contextPayload = {
      retryCount: 0,
      maxRetries: 3,
      retryDelay: 10,
      source,
      currentTime: 55,
      wasPlaying: true,
    }

    // Attempt 1: refresh the SABR session, keep playing on the same rung.
    const firstAction = await adapter.handleProviderRecovery(err, contextPayload)
    expect(firstAction).toBe('handled')
    expect(refresh).toHaveBeenCalledTimes(1)
    expect(player.retryStreaming).toHaveBeenCalledWith(0.1)
    expect(player.load).not.toHaveBeenCalledWith(fallbackSource, expect.anything(), 'application/dash+xml')

    // Attempt 2 (invalidation recurs): degrade to bundled DASH at the playhead.
    const secondAction = await adapter.handleProviderRecovery(err, contextPayload)
    expect(secondAction).toBe('handled')
    expect(player.load).toHaveBeenNthCalledWith(2, fallbackSource, 55, 'application/dash+xml')
    expect(video.play).toHaveBeenCalled()

    // Already degraded — subsequent errors must NOT re-degrade or re-refresh.
    refresh.mockClear()
    const thirdAction = await adapter.handleProviderRecovery(err, contextPayload)
    expect(thirdAction).toBeNull()
    expect(refresh).not.toHaveBeenCalled()
    adapter.destroy()
  })
})
