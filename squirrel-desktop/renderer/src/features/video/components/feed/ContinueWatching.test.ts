// @vitest-environment jsdom
import { createApp, defineComponent, h, nextTick } from 'vue'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import ContinueWatching from './ContinueWatching.vue'
import type { VideoHistoryEntry } from '@/features/video/types/video'

const { getWatchHistoryMock } = vi.hoisted(() => ({
  getWatchHistoryMock: vi.fn(),
}))

vi.mock('@/features/video/composables/useVideoHistory', () => ({
  useVideoHistory: () => ({ getWatchHistory: getWatchHistoryMock }),
}))
vi.mock('@/shared/icons/AppIcon.vue', () => ({ default: { render: () => null } }))
vi.mock('@/shared/components/layout/AppEmptyState.vue', () => ({
  default: defineComponent({ render: () => h('div') }),
}))
vi.mock('@/features/video/components/feed/VideoThumbnail.vue', () => ({
  default: defineComponent({ render: () => h('div', { class: 'thumbnail-stub' }) }),
}))
vi.mock('@/shared/ui/button', () => ({
  Button: defineComponent({
    props: {
      variant: String,
      size: String,
    },
    setup(_, { attrs, slots }) {
      return () => h('button', attrs, slots.default?.())
    },
  }),
}))

const mountedApps: Array<ReturnType<typeof createApp>> = []

const historyEntry = (id: number, lastPosition: number, duration = 1000): VideoHistoryEntry => ({
  id,
  history_id: id,
  title: `视频 ${id}`,
  url: `https://example.test/videos/${id}`,
  thumbnail: '',
  duration,
  last_position: lastPosition,
  played_at: '2026-07-19T00:00:00Z',
  uploaded_at: null,
  created_at: null,
  subscriptions: [{ id, name: `来源 ${id}`, url: '' }],
  actors: [],
  site: null,
})

beforeEach(() => {
  getWatchHistoryMock.mockReset()
})

afterEach(() => {
  mountedApps.splice(0).forEach((app) => app.unmount())
  document.body.replaceChildren()
})

const mountContinueWatching = (onOpenModal = vi.fn()) => {
  const host = document.createElement('div')
  document.body.append(host)
  const app = createApp({
    render: () => h(ContinueWatching, { onOpenModal }),
  })
  mountedApps.push(app)
  app.mount(host)
  return { host, onOpenModal }
}

describe('ContinueWatching', () => {
  it('shows only meaningful unfinished progress and opens the whole card', async () => {
    const barelyStarted = historyEntry(1, 5)
    const started = historyEntry(2, 10)
    const inProgress = historyEntry(3, 500)
    const nearlyFinished = historyEntry(4, 950)
    const completed = historyEntry(5, 1000)
    getWatchHistoryMock.mockResolvedValue({
      items: [barelyStarted, started, inProgress, nearlyFinished, completed],
      total: 5,
      page: 1,
      page_size: 30,
    })

    const { host, onOpenModal } = mountContinueWatching()

    await vi.waitFor(() => {
      expect(host.querySelectorAll('.continue-rail__card')).toHaveLength(2)
    })

    const cards = host.querySelectorAll<HTMLButtonElement>('.continue-rail__card')
    expect(getWatchHistoryMock).toHaveBeenCalledWith(1, { pageSize: 30 })
    expect(host.textContent).toContain('1%')
    expect(host.textContent).toContain('剩余')
    expect(host.textContent).not.toContain('视频 1')
    expect(host.textContent).not.toContain('视频 4')
    // 续播角标常驻 DOM，hover 才显示（触屏/减少动效下始终可见）
    expect(host.querySelector('.continue-rail__resume')).not.toBeNull()

    cards[0]?.click()
    await nextTick()
    expect(onOpenModal).toHaveBeenCalledOnce()
    expect(onOpenModal).toHaveBeenCalledWith(started)
  })
})
