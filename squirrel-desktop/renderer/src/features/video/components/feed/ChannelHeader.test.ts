// @vitest-environment jsdom
import { createApp, defineComponent, h, nextTick } from 'vue'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import ChannelHeader from './ChannelHeader.vue'

const mocks = vi.hoisted(() => ({
  getDetail: vi.fn(),
  unsubscribe: vi.fn(),
  updateSpecial: vi.fn(),
  directRefresh: vi.fn(),
  notifyRemoved: vi.fn(),
}))

vi.mock('@/shared/api', () => ({
  getSubscriptionDetail: mocks.getDetail,
  unsubscribe: mocks.unsubscribe,
  updateSpecialFollowStatus: mocks.updateSpecial,
  triggerDirectRefresh: mocks.directRefresh,
}))
vi.mock('@/shared/lib/subscriptionEvents', () => ({ notifySubscriptionRemoved: mocks.notifyRemoved }))
vi.mock('@/shared/composables/useDesktopBridge', () => ({ useDesktopBridge: () => ({ isDesktop: () => false }) }))
vi.mock('@/shared/icons/AppIcon.vue', () => ({ default: defineComponent({ render: () => h('i') }) }))
vi.mock('@/shared/ui/skeleton', () => ({
  Spinner: defineComponent({ render: () => h('i') }),
  Skeleton: defineComponent({ render: () => h('span', { 'data-skeleton': '' }) }),
}))
vi.mock('@/shared/components/AppActionMenu.vue', () => ({ default: defineComponent({ render: () => null }) }))
vi.mock('@/shared/components/layout/AppSegmentedControl.vue', () => ({ default: defineComponent({ render: () => null }) }))
vi.mock('@/features/video/components/SubscriptionAvatar.vue', () => ({ default: defineComponent({ render: () => h('span') }) }))
vi.mock('@/shared/ui/button', () => ({
  Button: defineComponent({
    inheritAttrs: false,
    setup(_, { attrs, slots }) {
      return () => h('button', { ...attrs, type: attrs.type || 'button' }, slots.default?.())
    },
  }),
}))
vi.mock('@/shared/components/ConfirmDialog.vue', () => ({
  default: defineComponent({
    props: { open: Boolean, title: String, description: String, confirming: Boolean },
    emits: ['confirm', 'update:open'],
    setup(props, { emit }) {
      return () => props.open
        ? h('section', { 'data-confirm': '' }, [
            h('p', props.title),
            h('p', props.description),
            h('button', { disabled: props.confirming, onClick: () => emit('confirm') }, '确认取消订阅'),
          ])
        : null
    },
  }),
}))

const detail = {
  id: 7,
  type: 'CHANNEL',
  name: '测试频道',
  url: 'https://video.example/channel/7',
  avatar: null,
  description: '频道说明',
  total_videos: 12,
  total_extract: 10,
  is_deleted: false,
  extra_data: null,
  created_at: '2026-08-01 08:00:00',
  updated_at: '2026-08-01 08:00:00',
  is_nsfw: false,
  is_special_followed: false,
  sync_status: 'idle',
  last_sync_at: '2026-08-01 08:00:00',
  last_success_at: '2026-08-01 08:00:00',
  next_sync_at: '2026-08-02 08:00:00',
  last_error: null,
  pending_video_count: 2,
  site: 'example',
}

const apps: Array<ReturnType<typeof createApp>> = []
const settle = async () => {
  await Promise.resolve()
  await nextTick()
  await Promise.resolve()
  await nextTick()
}

async function mountHeader() {
  const host = document.createElement('div')
  document.body.append(host)
  const app = createApp(ChannelHeader, { subscriptionId: 7 })
  apps.push(app)
  app.mount(host)
  await settle()
  return host
}

const button = (host: HTMLElement, text: string) => Array.from(host.querySelectorAll('button'))
  .find(item => item.textContent?.includes(text)) as HTMLButtonElement

beforeEach(() => {
  mocks.getDetail.mockResolvedValue({ ...detail })
  mocks.unsubscribe.mockResolvedValue({ is_subscribed: false, subscription_id: null })
  mocks.updateSpecial.mockResolvedValue(undefined)
})

afterEach(() => {
  apps.splice(0).forEach(app => app.unmount())
  document.body.replaceChildren()
  vi.clearAllMocks()
})

describe('ChannelHeader', () => {
  it('shows identity loading, reports detail failure, and retries', async () => {
    let reject!: (error: Error) => void
    mocks.getDetail.mockReturnValueOnce(new Promise((_, rejected) => { reject = rejected }))
    const mountPromise = mountHeader()
    await nextTick()
    expect(document.querySelector('[aria-label="频道信息加载中"]')).not.toBeNull()
    reject(new Error('详情服务不可用'))
    const host = await mountPromise

    expect(host.textContent).toContain('频道信息加载失败')
    expect(host.textContent).toContain('详情服务不可用')
    mocks.getDetail.mockResolvedValueOnce({ ...detail })
    button(host, '重试').click()
    await settle()
    expect(host.textContent).toContain('测试频道')
    expect(host.textContent).toContain('下次同步')
    expect(host.textContent).toContain('2 个视频')
  })

  it('requires confirmation and visibly reports unsubscribe failure', async () => {
    const host = await mountHeader()
    mocks.unsubscribe.mockRejectedValueOnce(new Error('无法取消订阅'))

    button(host, '取消订阅').click()
    await nextTick()
    expect(mocks.unsubscribe).not.toHaveBeenCalled()
    expect(host.querySelector('[data-confirm]')).not.toBeNull()

    button(host, '确认取消订阅').click()
    await settle()
    expect(mocks.unsubscribe).toHaveBeenCalledWith(7)
    expect(host.querySelector('[role="alert"]')?.textContent).toContain('无法取消订阅')
    expect(mocks.notifyRemoved).not.toHaveBeenCalled()
  })

  it('keeps special-follow state and visibly reports update failure', async () => {
    const host = await mountHeader()
    mocks.updateSpecial.mockRejectedValueOnce(new Error('特别关注保存失败'))

    host.querySelector<HTMLButtonElement>('[aria-label="切换特别关注"]')!.click()
    await settle()
    expect(mocks.updateSpecial).toHaveBeenCalledWith(7, true)
    expect(host.querySelector('[aria-label="切换特别关注"]')?.getAttribute('aria-pressed')).toBe('false')
    expect(host.querySelector('[role="alert"]')?.textContent).toContain('特别关注保存失败')
  })
})
