// @vitest-environment jsdom
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

const { getDesktopBridgeMock } = vi.hoisted(() => ({
  getDesktopBridgeMock: vi.fn(),
}))

vi.mock('@/shared/composables/useDesktopBridge', () => ({
  getDesktopBridge: getDesktopBridgeMock,
}))

vi.mock('@/shared/lib/logger', () => ({
  Logger: { debug: vi.fn(), error: vi.fn(), info: vi.fn(), warn: vi.fn() },
}))

import { prefetchDesktopPlaybackSource } from './useVideoOperations'

describe('prefetchDesktopPlaybackSource', () => {
  beforeEach(() => {
    getDesktopBridgeMock.mockReset()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('no-ops outside the desktop bridge', () => {
    getDesktopBridgeMock.mockReturnValue(null)
    prefetchDesktopPlaybackSource({
      id: 1,
      url: 'https://www.youtube.com/watch?v=dQw4w9WgXcQ',
    })
    expect(getDesktopBridgeMock).toHaveBeenCalled()
  })

  it('fires the matching desktop resolver when a YouTube url is present', async () => {
    const resolveYouTubePlayback = vi.fn().mockResolvedValue({ stream_type: 'sabr' })
    getDesktopBridgeMock.mockReturnValue({
      isDesktop: true,
      resolveYouTubePlayback,
    })

    prefetchDesktopPlaybackSource({
      id: 1,
      title: 'Never Gonna Give You Up',
      url: 'https://www.youtube.com/watch?v=dQw4w9WgXcQ',
    })

    await vi.waitFor(() => {
      expect(resolveYouTubePlayback).toHaveBeenCalledWith(
        'https://www.youtube.com/watch?v=dQw4w9WgXcQ',
        expect.objectContaining({
          forceRefresh: false,
          title: 'Never Gonna Give You Up',
        }),
      )
    })
  })

  it('skips urls that have no desktop provider', () => {
    const resolveYouTubePlayback = vi.fn()
    getDesktopBridgeMock.mockReturnValue({
      isDesktop: true,
      resolveYouTubePlayback,
    })

    prefetchDesktopPlaybackSource({
      id: 1,
      url: 'https://example.test/not-supported',
    })

    expect(resolveYouTubePlayback).not.toHaveBeenCalled()
  })
})
