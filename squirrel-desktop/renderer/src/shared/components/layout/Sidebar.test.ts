// @vitest-environment jsdom
/** Category landmarks remain present while collapsed navigation items become compact. */
import { createPinia } from 'pinia'
import { createApp, h, nextTick } from 'vue'
import { createMemoryHistory, createRouter } from 'vue-router'
import { afterEach, describe, expect, it, vi } from 'vitest'
import Sidebar from './Sidebar.vue'

vi.mock('@/shared/icons/AppIcon.vue', () => ({
  default: { render: () => null },
}))

const mountedApps: Array<ReturnType<typeof createApp>> = []

afterEach(() => {
  mountedApps.splice(0).forEach((app) => app.unmount())
  document.body.replaceChildren()
})

describe('Sidebar navigation structure', () => {
  it('keeps category groups and item order in the collapsed rail', async () => {
    const router = createRouter({
      history: createMemoryHistory(),
      routes: [{ path: '/:pathMatch(.*)*', component: { render: () => null } }],
    })
    await router.push('/rss')
    await router.isReady()

    const host = document.createElement('div')
    document.body.append(host)
    const app = createApp({ render: () => h(Sidebar, { collapsed: true }) })
    mountedApps.push(app)
    app.use(createPinia())
    app.use(router)
    app.mount(host)
    await nextTick()

    const mainNav = host.querySelector<HTMLElement>('.sidebar-nav')
    const labels = Array.from(mainNav?.querySelectorAll('.sidebar-item__label') ?? [])
      .map((label) => label.textContent)
    const categories = Array.from(mainNav?.querySelectorAll('.sidebar-group__label') ?? [])
      .map((label) => label.textContent?.trim())

    expect(labels).toEqual(['视频', '订阅', 'RSS', '音乐', '历史', '播放列表', '站点', '定时', '日志'])
    expect(categories).toEqual(['媒体', '资料库', '工具'])
    expect(mainNav?.querySelectorAll('.sidebar-group')).toHaveLength(categories.length)
  })
})
