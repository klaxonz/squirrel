import { ref } from 'vue'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { Router } from 'vue-router'

import useVideoPageNavigation from './useVideoPageNavigation'
import type { VideoPageVideo } from '@/features/playback/types/videoPlayback'

const { getRandomVideoMock } = vi.hoisted(() => ({
  getRandomVideoMock: vi.fn(),
}))

vi.mock('@/shared/api', () => ({
  getRandomVideo: getRandomVideoMock,
}))

vi.mock('@/features/video/composables/useVideoOperations', () => ({
  prefetchDesktopPlaybackSource: vi.fn(),
}))
const createNavigation = () => {
  const route = { params: { videoId: '1' } }
  const router = { replace: vi.fn().mockResolvedValue(undefined) } as unknown as Router
  const video = ref<VideoPageVideo | null>({ id: 1, title: '当前视频' })
  const navigation = useVideoPageNavigation({
    route,
    router,
    video,
    relatedVideos: ref([]),
    goToPrev: () => null,
    goToNext: () => null,
    onVideoEnded: vi.fn(),
  })
  return { router, ...navigation }
}

describe('useVideoPageNavigation random playback', () => {
  beforeEach(() => {
    getRandomVideoMock.mockReset()
  })

  it('navigates to a returned random video and reports success', async () => {
    getRandomVideoMock.mockResolvedValue({ id: 2, title: '随机视频' })
    const navigation = createNavigation()

    await expect(navigation.handlePlayRandom()).resolves.toBe(true)
    expect(navigation.router.replace).toHaveBeenCalledWith(expect.objectContaining({
      name: 'VideoPlay',
      params: { videoId: '2' },
    }))
  })

  it('reports failure after exhausting retries', async () => {
    getRandomVideoMock.mockRejectedValue(new Error('offline'))
    const navigation = createNavigation()

    await expect(navigation.handlePlayRandom()).resolves.toBe(false)
    expect(getRandomVideoMock).toHaveBeenCalledTimes(4)
    expect(navigation.router.replace).not.toHaveBeenCalled()
  })

  it('does not report success when the endpoint only returns the current video', async () => {
    getRandomVideoMock.mockResolvedValue({ id: '1', title: '当前视频' })
    const navigation = createNavigation()

    await expect(navigation.handlePlayRandom()).resolves.toBe(false)
    expect(getRandomVideoMock).toHaveBeenCalledTimes(4)
    expect(navigation.router.replace).not.toHaveBeenCalled()
  })
})
