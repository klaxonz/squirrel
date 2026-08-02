// @vitest-environment jsdom
import { createApp, defineComponent, nextTick, ref } from 'vue'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import RemoteChannelDetail from './RemoteChannelDetail.vue'

const mocks = vi.hoisted(() => ({
  route: {
    name: 'RemoteChannelDetail',
    query: {
      site: 'youtube',
      url: 'https://youtube.com/@channel',
      name: '测试频道',
    } as Record<string, string>,
  },
  push: vi.fn(),
  status: vi.fn(),
  subscribe: vi.fn(),
  unsubscribe: vi.fn(),
  rememberSeed: vi.fn(),
  prefetch: vi.fn(),
  getRemoteChannel: vi.fn(),
}))

vi.mock('vue-router', () => ({
  useRoute: () => mocks.route,
  useRouter: () => ({ push: mocks.push }),
}))
vi.mock('@/shared/api', () => ({
  getSubscriptionStatus: mocks.status,
  subscribe: mocks.subscribe,
  unsubscribe: mocks.unsubscribe,
}))
vi.mock('@/features/video/composables/videoPlaybackSeed', () => ({
  rememberVideoPlaybackSeed: mocks.rememberSeed,
}))
vi.mock('@/features/video/composables/useVideoOperations', () => ({
  prefetchDesktopPlaybackSource: mocks.prefetch,
}))
vi.mock('@/features/video/composables/useSkeletonCount', () => ({
  useSkeletonCount: () => ({ count: ref(2), attachRef: ref<HTMLElement | null>(null) }),
}))
vi.mock('@/shared/composables/useMainScrollRoot', () => ({
  getMainScrollRoot: () => null,
}))
vi.mock('@/shared/composables/useDesktopBridge', () => ({
  useDesktopBridge: () => ({ isDesktop: () => true }),
}))
vi.mock('@/shared/icons/AppIcon.vue', () => ({
  default: defineComponent({ template: '<span aria-hidden="true" />' }),
}))
vi.mock('@/features/video/components/SubscriptionAvatar.vue', () => ({
  default: defineComponent({ template: '<span class="avatar" />' }),
}))
vi.mock('@/features/video/components/feed/VideoThumbnail.vue', () => ({
  default: defineComponent({ template: '<span class="thumbnail" />' }),
}))
vi.mock('@/features/video/components/feed/VideoSkeleton.vue', () => ({
  default: defineComponent({ template: '<span class="skeleton" />' }),
}))
vi.mock('@/shared/components/layout/AppPageShell.vue', () => ({
  default: defineComponent({ template: '<main><slot /></main>' }),
}))

class IntersectionObserverStub {
  observe() {}
  disconnect() {}
}

const apps: Array<ReturnType<typeof createApp>> = []
const flushPromises = () => new Promise<void>((resolve) => setTimeout(resolve, 0))

const mountPage = () => {
  const host = document.createElement('div')
  document.body.append(host)
  const app = createApp(RemoteChannelDetail)
  apps.push(app)
  app.mount(host)
  return host
}

beforeEach(() => {
  vi.clearAllMocks()
  vi.stubGlobal('IntersectionObserver', IntersectionObserverStub)
  Object.defineProperty(window, 'desktopApp', {
    configurable: true,
    value: { getRemoteChannel: mocks.getRemoteChannel },
  })
  mocks.status.mockResolvedValue({ is_subscribed: false, subscription_id: null })
})

afterEach(() => {
  apps.splice(0).forEach((app) => app.unmount())
  document.body.replaceChildren()
  vi.unstubAllGlobals()
})

describe('RemoteChannelDetail', () => {
  it('deduplicates results and renders playable, external, and unavailable actions', async () => {
    mocks.getRemoteChannel.mockResolvedValue({
      profile: { name: '测试频道', url: mocks.route.query.url },
      has_more: false,
      items: [
        { source: 'remote', site: 'youtube', title: '可播放', url: 'https://youtube.com/watch?v=1' },
        { source: 'remote', site: 'youtube', title: '重复项', url: 'https://youtube.com/watch?v=1' },
        { source: 'remote', site: 'youtube', title: '外链', url: 'https://example.com/video' },
        { source: 'remote', site: 'youtube', title: '不可用', url: 'not-a-url' },
      ],
    })

    const host = mountPage()
    await flushPromises()
    await nextTick()

    expect(host.querySelectorAll('.remote-channel-card')).toHaveLength(3)
    expect(host.querySelector('.remote-channel-primary-action')?.textContent).toContain('播放')
    expect(host.querySelector<HTMLAnchorElement>('.remote-channel-external-action')?.href).toBe('https://example.com/video')
    expect(host.querySelector('.remote-channel-disabled-action')).not.toBeNull()
    expect(host.textContent).toContain('已加载全部 3 个视频')

    host.querySelector<HTMLButtonElement>('.remote-channel-primary-action')!.click()
    await nextTick()
    expect(mocks.rememberSeed).toHaveBeenCalledOnce()
    expect(mocks.push).toHaveBeenCalledWith(expect.objectContaining({ name: 'VideoPlay' }))
  })

  it('shows subscription failures and retries the failed status request', async () => {
    mocks.getRemoteChannel.mockResolvedValue({ profile: { name: '测试频道' }, items: [], has_more: false })
    mocks.status
      .mockRejectedValueOnce(new Error('status unavailable'))
      .mockResolvedValueOnce({ is_subscribed: true, subscription_id: 9 })

    const host = mountPage()
    await flushPromises()
    await nextTick()

    const alert = host.querySelector<HTMLElement>('[role="alert"]')!
    expect(alert.textContent).toContain('status unavailable')
    alert.querySelector<HTMLButtonElement>('button')!.click()
    await flushPromises()
    await nextTick()

    expect(mocks.status).toHaveBeenCalledTimes(2)
    expect(host.querySelector('[role="alert"]')).toBeNull()
    expect(host.textContent).toContain('已订阅此频道')
  })
})
