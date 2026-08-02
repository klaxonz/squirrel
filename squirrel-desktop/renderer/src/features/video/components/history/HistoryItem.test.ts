// @vitest-environment jsdom
import { createApp, defineComponent, h, nextTick } from 'vue'
import { afterEach, describe, expect, it, vi } from 'vitest'
import HistoryItem from './HistoryItem.vue'
import type { VideoHistoryEntry } from '@/features/video/types/video'

const { prefetchDesktopPlaybackSourceMock } = vi.hoisted(() => ({
  prefetchDesktopPlaybackSourceMock: vi.fn(),
}))

vi.mock('@/features/video/composables/useVideoOperations', () => ({
  prefetchDesktopPlaybackSource: prefetchDesktopPlaybackSourceMock,
}))
vi.mock('@/shared/icons/AppIcon.vue', () => ({ default: { render: () => null } }))
vi.mock('@/features/video/components/SubscriptionAvatar.vue', () => ({
  default: defineComponent({ render: () => h('span', { class: 'avatar-stub' }) }),
}))
vi.mock('@/features/video/components/feed/VideoThumbnail.vue', () => ({
  default: defineComponent({ render: () => h('div', { class: 'thumbnail-stub' }) }),
}))
vi.mock('@/shared/ui/button', () => ({
  Button: defineComponent({
    setup(_, { attrs, slots }) {
      return () => h('button', attrs, slots.default?.())
    },
  }),
}))

const mountedApps: Array<ReturnType<typeof createApp>> = []

const video: VideoHistoryEntry = {
  id: 42,
  history_id: 84,
  title: '历史项目语义测试',
  url: 'https://example.test/video/42',
  thumbnail: '',
  duration: 120,
  last_position: 30,
  played_at: '2026-07-19T00:00:00Z',
  uploaded_at: null,
  created_at: null,
  subscriptions: [{ id: 7, name: '测试频道', url: 'https://example.test/channel/7' }],
  actors: [],
  site: 'youtube',
}

afterEach(() => {
  mountedApps.splice(0).forEach((app) => app.unmount())
  document.body.replaceChildren()
  prefetchDesktopPlaybackSourceMock.mockReset()
})

function mountHistoryItem() {
  const onOpen = vi.fn()
  const onOpenProfile = vi.fn()
  const onDelete = vi.fn()
  const host = document.createElement('div')
  document.body.append(host)
  const app = createApp({
    render: () => h(HistoryItem, { video, onOpen, onOpenProfile, onDelete }),
  })
  mountedApps.push(app)
  app.mount(host)
  return { host, onOpen, onOpenProfile, onDelete }
}

const dispatchKey = (target: Element, key: 'Enter' | ' ') => {
  target.dispatchEvent(new KeyboardEvent('keydown', { key, bubbles: true, cancelable: true }))
}

describe('HistoryItem row semantics', () => {
  it('uses a native primary button and preserves prefetch activation', async () => {
    const { host, onOpen } = mountHistoryItem()
    const shell = host.querySelector<HTMLElement>('.history-item__open')
    const openButton = host.querySelector<HTMLButtonElement>('.history-item__open-button')

    expect(host.querySelector('article.history-item')?.hasAttribute('tabindex')).toBe(false)
    expect(shell?.getAttribute('role')).toBeNull()
    expect(openButton?.tagName).toBe('BUTTON')

    shell?.dispatchEvent(new PointerEvent('pointerenter', { bubbles: true }))
    shell?.dispatchEvent(new PointerEvent('pointerdown', { bubbles: true, button: 0 }))
    openButton?.click()
    await nextTick()

    expect(prefetchDesktopPlaybackSourceMock).toHaveBeenCalledTimes(2)
    expect(prefetchDesktopPlaybackSourceMock).toHaveBeenCalledWith(video)
    expect(onOpen).toHaveBeenCalledOnce()
    expect(onOpen).toHaveBeenCalledWith(video)
  })

  it('keeps profile and delete keyboard events from opening the item', async () => {
    const { host, onOpen, onOpenProfile, onDelete } = mountHistoryItem()
    const profileButton = host.querySelector<HTMLButtonElement>('.history-item__source--link')
    const deleteButton = host.querySelector<HTMLButtonElement>('.history-item__delete')

    expect(profileButton?.tagName).toBe('BUTTON')
    expect(deleteButton?.tagName).toBe('BUTTON')

    for (const key of ['Enter', ' '] as const) {
      if (profileButton) dispatchKey(profileButton, key)
      if (deleteButton) dispatchKey(deleteButton, key)
    }
    await nextTick()

    expect(onOpen).not.toHaveBeenCalled()

    profileButton?.click()
    deleteButton?.click()
    await nextTick()

    expect(onOpen).not.toHaveBeenCalled()
    expect(onOpenProfile).toHaveBeenCalledOnce()
    expect(onOpenProfile).toHaveBeenCalledWith(expect.objectContaining({ name: '测试频道' }))
    expect(onDelete).toHaveBeenCalledOnce()
    expect(onDelete).toHaveBeenCalledWith(video.history_id)
  })
})
