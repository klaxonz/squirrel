// @vitest-environment jsdom
/** Video cards activate playback directly without stealing nested actions. */
import { createApp, h, nextTick } from 'vue'
import { afterEach, describe, expect, it, vi } from 'vitest'
import VideoItem from './VideoItem.vue'
import type { VideoListItem } from '@/features/video/types/video'

const { prefetchDesktopPlaybackSourceMock } = vi.hoisted(() => ({
  prefetchDesktopPlaybackSourceMock: vi.fn(),
}))

vi.mock('@/features/video/composables/useVideoOperations', () => ({
  prefetchDesktopPlaybackSource: prefetchDesktopPlaybackSourceMock,
}))
vi.mock('@/shared/icons/AppIcon.vue', () => ({ default: { render: () => null } }))
vi.mock('@/features/video/components/SubscriptionAvatar.vue', () => ({ default: { render: () => null } }))
vi.mock('@/features/video/components/feed/VideoThumbnail.vue', () => ({ default: { render: () => null } }))
vi.mock('./ContextMenu.vue', () => ({ default: { render: () => null } }))
vi.mock('@/shared/api', () => ({ updateVideoReadState: vi.fn().mockResolvedValue(undefined) }))
vi.mock('@/shared/composables/useSystemConfig', () => ({
  useSystemConfig: () => ({ config: { value: { blur_nsfw_thumbnails: false } } }),
}))
vi.mock('@/shared/components/toast/useToast', () => ({
  useToast: () => ({ error: vi.fn() }),
}))
vi.mock('@/features/video/composables/useVideoInteraction', () => ({
  default: () => ({
    INTERACTION_TYPE: { LIKE: 1, LATER: 3 },
    toggleLike: vi.fn().mockResolvedValue(undefined),
    deleteInteraction: vi.fn().mockResolvedValue(undefined),
  }),
}))

const mountedApps: Array<ReturnType<typeof createApp>> = []

afterEach(() => {
  mountedApps.splice(0).forEach((app) => app.unmount())
  document.body.replaceChildren()
  prefetchDesktopPlaybackSourceMock.mockReset()
})

function mountVideoItem(onOpen: (video: VideoListItem) => void, overrides: Partial<VideoListItem> = {}) {
  const video: VideoListItem = {
    id: 42,
    title: '直接播放测试',
    url: 'https://example.test/video/42',
    thumbnail: '',
    duration: null,
    last_position: 0,
    uploaded_at: null,
    created_at: '2026-07-19T00:00:00Z',
    subscriptions: [],
    actors: [],
    is_read: false,
    interaction_type: null,
    ...overrides,
  }
  const host = document.createElement('div')
  document.body.append(host)
  const app = createApp({
    render: () => h(VideoItem, { video, onOpenModal: onOpen }),
  })
  mountedApps.push(app)
  app.mount(host)
  return { host, video }
}

describe('VideoItem playback activation', () => {
  it('opens playback on click and Enter while nested quick actions stay independent', async () => {
    const onOpen = vi.fn()
    const { host, video } = mountVideoItem(onOpen)
    const card = host.querySelector<HTMLElement>('.video-item')
    expect(card).not.toBeNull()

    card?.click()
    card?.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', bubbles: true, cancelable: true }))
    await nextTick()

    expect(onOpen).toHaveBeenCalledTimes(2)
    expect(onOpen).toHaveBeenNthCalledWith(1, video)
    expect(onOpen).toHaveBeenNthCalledWith(2, video)

    host.querySelector<HTMLButtonElement>('.video-item__quick-btn')?.click()
    await nextTick()
    expect(onOpen).toHaveBeenCalledTimes(2)
  })

  it('keeps playback progress on the thumbnail without interaction badges', () => {
    const { host } = mountVideoItem(vi.fn(), {
      duration: 120,
      last_position: 30,
      is_read: true,
      interaction_type: 1,
    })

    expect(host.querySelector('.video-item__progress')).not.toBeNull()
    expect(host.querySelector('.video-item__flags')).toBeNull()
  })

  it('prefetches desktop playback on hover and left pointerdown', async () => {
    const { host, video } = mountVideoItem(vi.fn(), {
      url: 'https://www.youtube.com/watch?v=dQw4w9WgXcQ',
    })
    const card = host.querySelector<HTMLElement>('.video-item')
    expect(card).not.toBeNull()

    card?.dispatchEvent(new PointerEvent('pointerenter', { bubbles: true }))
    card?.dispatchEvent(new PointerEvent('pointerdown', { bubbles: true, button: 0 }))
    await nextTick()

    expect(prefetchDesktopPlaybackSourceMock).toHaveBeenCalledTimes(2)
    expect(prefetchDesktopPlaybackSourceMock).toHaveBeenNthCalledWith(1, expect.objectContaining({
      id: video.id,
      url: 'https://www.youtube.com/watch?v=dQw4w9WgXcQ',
    }))
  })
})
