import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import type { StreamContext } from '../core/StreamAdapter'
import type { StreamSink } from '../core/StreamSink'
import type { PlayerState } from '../core/types'

const shakaMockState = vi.hoisted(() => ({
  latestPlayer: null as unknown,
  audioTracks: [] as Array<Record<string, unknown>>,
}))

vi.mock('shaka-player', () => {
  const track = {
    id: 137,
    type: 'variant',
    active: true,
    width: 1920,
    height: 1080,
    bandwidth: 2_000_000,
    videoCodec: 'avc1.640028',
  }
  const networkingEngine = {
    registerRequestFilter: vi.fn(),
    registerResponseFilter: vi.fn(),
    request: vi.fn(),
  }

  class MockPlayer {
    attach = vi.fn(async () => {})
    configure = vi.fn()
    load = vi.fn(async () => {})
    destroy = vi.fn(async () => {})
    addEventListener = vi.fn()
    getVariantTracks = vi.fn(() => [track])
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
      expect.objectContaining({ id: 137, active: true }),
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
})
