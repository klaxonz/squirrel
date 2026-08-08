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

const createNavigation = (options: { relatedVideos?: VideoPageVideo[] } = {}) => {
  const route = { name: 'VideoPlay', params: { videoId: '1' } }
  const router = { replace: vi.fn().mockResolvedValue(undefined) } as unknown as Router
  const video = ref<VideoPageVideo | null>({ id: 1, title: '当前视频' })
  const navigation = useVideoPageNavigation({
    route,
    router,
    video,
    relatedVideos: ref(options.relatedVideos ?? []),
    goToPrev: () => null,
    goToNext: () => null,
    onVideoEnded: vi.fn(),
  })
  return { router, route, ...navigation }
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

  it('does not navigate once the user has left the play page', async () => {
    getRandomVideoMock.mockResolvedValue({ id: 2, title: '随机视频' })
    const navigation = createNavigation()
    navigation.route.name = 'AllVideos' // 用户在请求期间按了返回

    await expect(navigation.handlePlayRandom()).resolves.toBe(true)
    expect(navigation.router.replace).not.toHaveBeenCalled()
  })
})

describe('useVideoPageNavigation autoplay chain', () => {
  beforeEach(() => {
    getRandomVideoMock.mockReset()
  })

  it('navigates to the next related video when the routed video is unchanged', async () => {
    const navigation = createNavigation({ relatedVideos: [{ id: 2, title: '相关视频' }] })

    await navigation.handleAutoplayNext()

    expect(navigation.router.replace).toHaveBeenCalledWith(expect.objectContaining({
      name: 'VideoPlay',
      params: { videoId: '2' },
    }))
  })

  it('abandons the chain when the routed video changed during the report flush', async () => {
    const navigation = createNavigation({ relatedVideos: [{ id: 2, title: '相关视频' }] })
    navigation.route.params.videoId = '2' // 上报等待期间用户已切到另一个视频

    await navigation.handleAutoplayNext()

    expect(navigation.router.replace).not.toHaveBeenCalled()
  })

  it('abandons the chain once the play page is no longer current', async () => {
    const navigation = createNavigation({ relatedVideos: [{ id: 2, title: '相关视频' }] })
    navigation.route.name = 'AllVideos' // 用户按返回离开了播放页

    await navigation.handleAutoplayNext()

    expect(navigation.router.replace).not.toHaveBeenCalled()
  })
})
