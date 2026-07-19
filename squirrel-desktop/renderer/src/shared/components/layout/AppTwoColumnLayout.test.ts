// @vitest-environment jsdom
import { createApp, defineComponent, h, nextTick, ref } from 'vue'
import { afterEach, describe, expect, it } from 'vitest'
import AppTwoColumnLayout from './AppTwoColumnLayout.vue'

const mountedApps: Array<ReturnType<typeof createApp>> = []

afterEach(() => {
  mountedApps.splice(0).forEach((app) => app.unmount())
  document.body.replaceChildren()
})

describe('AppTwoColumnLayout sidebar state', () => {
  it('collapses and restores the sidebar without unmounting its content', async () => {
    const sidebarCollapsed = ref(false)
    const TestHost = defineComponent({
      setup() {
        return () => h(
          AppTwoColumnLayout,
          { sidebarAlways: true, sidebarCollapsed: sidebarCollapsed.value },
          {
            sidebar: () => h('span', { 'data-testid': 'sidebar-content' }, 'Library'),
            default: () => h('span', 'Reader'),
          },
        )
      },
    })
    const host = document.createElement('div')
    document.body.append(host)
    const app = createApp(TestHost)
    mountedApps.push(app)
    app.mount(host)

    const layout = host.querySelector('.app-two-column')
    expect(layout?.classList.contains('app-two-column--sidebar-collapsed')).toBe(false)
    expect(host.querySelector('[data-testid="sidebar-content"]')).not.toBeNull()

    sidebarCollapsed.value = true
    await nextTick()
    expect(layout?.classList.contains('app-two-column--sidebar-collapsed')).toBe(true)
    expect(host.querySelector('[data-testid="sidebar-content"]')).not.toBeNull()

    sidebarCollapsed.value = false
    await nextTick()
    expect(layout?.classList.contains('app-two-column--sidebar-collapsed')).toBe(false)
  })
})
