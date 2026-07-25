import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import type { StreamContext } from '../core/StreamAdapter'
import type { StreamSink } from '../core/StreamSink'
import type { PlayerState } from '../core/types'

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

  it('pins FreeTube-style 720p startup quality without disabling ABR', async () => {
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
    // 1080p/4K before the pin; defaultBandwidthEstimate still seeds ~720p.
    expect(player.configure).toHaveBeenCalledWith(expect.objectContaining({
      abr: expect.objectContaining({
        enabled: false,
        defaultBandwidthEstimate: 2_000_000,
      }),
    }))
    // Opening track was 144p; pin exact 720p without clearing buffer.
    expect(player.selectVariantTrack).toHaveBeenCalledWith(
      expect.objectContaining({ id: 247, height: 720 }),
      false,
      0,
    )
    // ABR re-enabled after the pin so quality can still climb.
    expect(player.configure).toHaveBeenCalledWith({ abr: { enabled: true } })
    adapter.destroy()
  })

  it('downshifts a warm 1080p active track to 720p before first media', async () => {
    // Warm ABR case: prior throughput left 1080p as the active opening track.
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
    expect(player.selectVariantTrack).toHaveBeenCalledWith(
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
})
