// @vitest-environment jsdom
import { createApp, defineComponent, h, nextTick, ref } from 'vue'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import RemoteSearchResults from './RemoteSearchResults.vue'

const mocks = vi.hoisted(() => ({
  push: vi.fn().mockResolvedValue(undefined),
  rememberVideoPlaybackSeed: vi.fn(),
  prefetchDesktopPlaybackSource: vi.fn(),
}))

vi.mock('vue-router', () => ({ useRouter: () => ({ push: mocks.push }) }))
vi.mock('@/features/video/composables/videoPlaybackSeed', () => ({
  rememberVideoPlaybackSeed: mocks.rememberVideoPlaybackSeed,
}))
vi.mock('@/features/video/composables/useVideoOperations', () => ({
  prefetchDesktopPlaybackSource: mocks.prefetchDesktopPlaybackSource,
}))
vi.mock('@/features/video/composables/useSkeletonCount', () => ({
  useSkeletonCount: () => ({ count: ref(1), attachRef: ref<HTMLElement | null>(null) }),
}))
vi.mock('@/shared/composables/useInfiniteScrollSentinel', () => ({
  useInfiniteScrollSentinel: vi.fn(),
}))
vi.mock('@/shared/composables/useMainScrollRoot', () => ({ getMainScrollRoot: () => null }))
vi.mock('@/shared/components/layout/AppEmptyState.vue', () => ({
  default: defineComponent({ render: () => h('div') }),
}))
vi.mock('@/features/video/components/SubscriptionAvatar.vue', () => ({
  default: defineComponent({ render: () => h('span', { class: 'avatar-stub' }) }),
}))
vi.mock('./VideoSkeleton.vue', () => ({ default: defineComponent({ render: () => h('div') }) }))
vi.mock('./VideoThumbnail.vue', () => ({
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
const searchRemoteVideos = vi.fn()

const result = {
  source: 'remote' as const,
  site: 'youtube',
  title: '远端项目语义测试',
  url: 'https://www.youtube.com/watch?v=semantic-test',
  thumbnail: '',
  duration: 90,
  subscriptions: [{
    id: 9,
    name: '远端频道',
    url: 'https://www.youtube.com/@remote-channel',
    avatar: '',
  }],
  actors: [],
}

beforeEach(() => {
  Object.defineProperty(window, 'desktopApp', {
    configurable: true,
    value: { isDesktop: true, searchRemoteVideos },
  })
  searchRemoteVideos.mockResolvedValue({ items: [result], has_more: false })
  Object.values(mocks).forEach((mock) => mock.mockClear())
})

afterEach(() => {
  mountedApps.splice(0).forEach((app) => app.unmount())
  document.body.replaceChildren()
})

async function mountResults() {
  const host = document.createElement('div')
  document.body.append(host)
  const app = createApp({ render: () => h(RemoteSearchResults, { query: 'semantic' }) })
  mountedApps.push(app)
  app.mount(host)
  await vi.waitFor(() => expect(host.querySelector('.remote-search-item')).not.toBeNull())
  return host
}

const dispatchKey = (target: Element, key: 'Enter' | ' ') => {
  target.dispatchEvent(new KeyboardEvent('keydown', { key, bubbles: true, cancelable: true }))
}

describe('RemoteSearchResults row semantics', () => {
  it('uses a noninteractive shell with a native primary playback button', async () => {
    const host = await mountResults()
    const shell = host.querySelector<HTMLElement>('.remote-search-item')
    const openButton = host.querySelector<HTMLButtonElement>('.remote-search-item__open')

    expect(shell?.getAttribute('role')).toBeNull()
    expect(shell?.hasAttribute('tabindex')).toBe(false)
    expect(openButton?.tagName).toBe('BUTTON')

    openButton?.click()
    await nextTick()

    expect(mocks.rememberVideoPlaybackSeed).toHaveBeenCalledOnce()
    expect(mocks.prefetchDesktopPlaybackSource).toHaveBeenCalledOnce()
    expect(mocks.push).toHaveBeenCalledOnce()
    expect(mocks.push).toHaveBeenCalledWith(expect.objectContaining({
      name: 'VideoPlay',
      params: { videoId: expect.stringMatching(/^remote-youtube-/) },
    }))
  })

  it('keeps bubbling Enter and Space from the channel button from opening playback', async () => {
    const host = await mountResults()
    const channelButton = host.querySelector<HTMLButtonElement>('.remote-search-source-button')
    expect(channelButton?.tagName).toBe('BUTTON')

    for (const key of ['Enter', ' '] as const) {
      if (channelButton) dispatchKey(channelButton, key)
    }
    await nextTick()

    expect(mocks.rememberVideoPlaybackSeed).not.toHaveBeenCalled()
    expect(mocks.prefetchDesktopPlaybackSource).not.toHaveBeenCalled()
    expect(mocks.push).not.toHaveBeenCalled()

    channelButton?.click()
    await nextTick()

    expect(mocks.rememberVideoPlaybackSeed).not.toHaveBeenCalled()
    expect(mocks.prefetchDesktopPlaybackSource).not.toHaveBeenCalled()
    expect(mocks.push).toHaveBeenCalledOnce()
    expect(mocks.push).toHaveBeenCalledWith(expect.objectContaining({
      name: 'RemoteChannelDetail',
      query: expect.objectContaining({ site: 'youtube', name: '远端频道' }),
    }))
  })
})
