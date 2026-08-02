// @vitest-environment jsdom
import { createApp, defineComponent, h, nextTick } from 'vue'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import CreatorHeader from './CreatorHeader.vue'

const mocks = vi.hoisted(() => ({ getDetail: vi.fn() }))
vi.mock('@/shared/api', () => ({ getCreatorDetail: mocks.getDetail }))
vi.mock('@/shared/icons/AppIcon.vue', () => ({ default: defineComponent({ render: () => h('i') }) }))
vi.mock('@/shared/components/AppSkeleton.vue', () => ({ default: defineComponent({ render: () => h('span', { 'data-skeleton': '' }) }) }))
vi.mock('@/features/video/components/SubscriptionAvatar.vue', () => ({ default: defineComponent({ render: () => h('span') }) }))
vi.mock('@/shared/ui/button', () => ({
  Button: defineComponent({
    inheritAttrs: false,
    setup(_, { attrs, slots }) {
      return () => h('button', { ...attrs, type: 'button' }, slots.default?.())
    },
  }),
}))

const creator = {
  id: 4,
  name: '创作者甲',
  url: 'https://creator.example/u/4',
  avatar: null,
  description: '创作者简介',
  extra_data: { site_name: '示例站点' },
  total_videos: 8,
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
  const app = createApp(CreatorHeader, { creatorId: 4 })
  apps.push(app)
  app.mount(host)
  return host
}

beforeEach(() => mocks.getDetail.mockResolvedValue({ ...creator }))
afterEach(() => {
  apps.splice(0).forEach(app => app.unmount())
  document.body.replaceChildren()
  vi.clearAllMocks()
})

describe('CreatorHeader', () => {
  it('shows a loading identity and loaded source metadata', async () => {
    let resolve!: (value: typeof creator) => void
    mocks.getDetail.mockReturnValueOnce(new Promise(resolved => { resolve = resolved }))
    const host = await mountHeader()
    await nextTick()
    expect(host.querySelector('[aria-label="创作者信息加载中"]')).not.toBeNull()

    resolve({ ...creator })
    await settle()
    expect(host.textContent).toContain('创作者甲')
    expect(host.textContent).toContain('示例站点')
    expect(host.textContent).toContain('访问主页')
  })

  it('shows a retryable error and recovers', async () => {
    mocks.getDetail.mockRejectedValueOnce(new Error('创作者接口离线'))
    const host = await mountHeader()
    await settle()
    expect(host.querySelector('[role="alert"]')?.textContent).toContain('创作者接口离线')

    mocks.getDetail.mockResolvedValueOnce({ ...creator })
    Array.from(host.querySelectorAll('button')).find(item => item.textContent?.includes('重试'))!.click()
    await settle()
    expect(host.textContent).toContain('创作者甲')
    expect(host.querySelector('[role="alert"]')).toBeNull()
  })
})
