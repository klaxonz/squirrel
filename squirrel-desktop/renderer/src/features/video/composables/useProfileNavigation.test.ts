import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { Router } from 'vue-router'

const {
  rememberVideoPlaybackSeedMock,
  prefetchDesktopPlaybackSourceMock,
} = vi.hoisted(() => ({
  rememberVideoPlaybackSeedMock: vi.fn(),
  prefetchDesktopPlaybackSourceMock: vi.fn(),
}))

vi.mock('@/features/video/composables/videoPlaybackSeed', () => ({
  rememberVideoPlaybackSeed: rememberVideoPlaybackSeedMock,
}))

vi.mock('@/features/video/composables/useVideoOperations', () => ({
  prefetchDesktopPlaybackSource: prefetchDesktopPlaybackSourceMock,
}))

import { useProfileNavigation } from './useProfileNavigation'

describe('useProfileNavigation openVideo', () => {
  beforeEach(() => {
    rememberVideoPlaybackSeedMock.mockReset()
    prefetchDesktopPlaybackSourceMock.mockReset()
  })

  it('seeds the full list payload and prefetches desktop resolve before navigate', () => {
    const router = { push: vi.fn() } as unknown as Router
    const { openVideo } = useProfileNavigation(router)
    const video = {
      id: 7,
      title: 'list item',
      url: 'https://www.youtube.com/watch?v=dQw4w9WgXcQ',
    }

    openVideo(video)

    expect(rememberVideoPlaybackSeedMock).toHaveBeenCalledWith(video)
    expect(prefetchDesktopPlaybackSourceMock).toHaveBeenCalledWith(video)
    expect(router.push).toHaveBeenCalledWith({
      name: 'VideoPlay',
      params: { videoId: '7' },
    })
  })
})
