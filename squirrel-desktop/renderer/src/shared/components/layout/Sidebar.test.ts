// @vitest-environment jsdom
/** Category landmarks remain present while collapsed navigation items become compact. */
import { createPinia } from 'pinia'
import { createApp, nextTick } from 'vue'
import { createMemoryHistory, createRouter } from 'vue-router'
import { afterEach, describe, expect, it, vi } from 'vitest'
import Sidebar from './Sidebar.vue'
import SidebarMenuItem from './SidebarMenuItem.vue'
import { NAV_ITEMS } from '@/shared/constants/sidebar'
import {
  currentEntry,
  pushEntry,
  reset as resetNavigationHistory,
} from '@/shared/lib/navigationHistory'

vi.mock('@/shared/icons/AppIcon.vue', () => ({
  default: { render: () => null },
}))

const mountedApps: Array<ReturnType<typeof createApp>> = []

afterEach(() => {
  mountedApps.splice(0).forEach((app) => app.unmount())
  document.body.replaceChildren()
  resetNavigationHistory()
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
    // eslint-disable-next-line vue/one-component-per-file -- imported SFC test mount, not a component declaration
    const app = createApp(Sidebar, { collapsed: true })
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
    expect(categories).toEqual(['信息流', '我的', '运维'])
    expect(mainNav?.querySelectorAll('.sidebar-group')).toHaveLength(categories.length)
  })

  it('returns to the existing video list entry instead of reopening it at the top', async () => {
    const router = createRouter({
      history: createMemoryHistory(),
      routes: [
        { path: '/videos/all', name: 'AllVideos', component: { render: () => null } },
        { path: '/video/:id', name: 'VideoPlay', component: { render: () => null } },
      ],
    })
    await router.push('/video/42')
    await router.isReady()

    const listEntry = pushEntry({
      fullPath: '/videos/all',
      name: 'AllVideos',
      title: '全部视频',
      breadcrumbs: [],
      sectionLabel: '视频',
      scrollY: 15_000,
    })
    // A section can contain several consecutive playback entries (for example
    // when opening related videos). The sidebar must skip all of them and find
    // the original list even when it is outside the 10-item history menu.
    for (let index = 0; index < 11; index += 1) {
      pushEntry({
        fullPath: `/video/related-${index}`,
        name: 'VideoPlay',
        title: `相关视频 ${index}`,
        breadcrumbs: [],
        sectionLabel: '视频',
        scrollY: 0,
      })
    }
    pushEntry({
      fullPath: '/video/42',
      name: 'VideoPlay',
      title: '视频播放',
      breadcrumbs: [],
      sectionLabel: '视频',
      scrollY: 0,
    })

    const videoItem = NAV_ITEMS.find((item) => item.key === 'videos')
    expect(videoItem).toBeDefined()

    const host = document.createElement('div')
    document.body.append(host)
    // eslint-disable-next-line vue/one-component-per-file -- imported SFC test mount, not a component declaration
    const app = createApp(SidebarMenuItem, {
      item: videoItem!,
      isActive: true,
    })
    mountedApps.push(app)
    app.use(createPinia())
    app.use(router)
    app.mount(host)
    await nextTick()

    host.querySelector<HTMLAnchorElement>('.sidebar-item')?.click()
    await nextTick()
    await new Promise((resolve) => setTimeout(resolve, 0))

    expect(router.currentRoute.value.fullPath).toBe('/videos/all')
    expect(currentEntry()).toMatchObject({
      id: listEntry.id,
      scrollY: 15_000,
    })
  })
})
