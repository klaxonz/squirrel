// @vitest-environment jsdom
import { createApp, defineComponent, h, nextTick, ref } from 'vue'
import { afterEach, describe, expect, it } from 'vitest'
import AppTwoColumnLayout from './AppTwoColumnLayout.vue'

const mountedApps: Array<ReturnType<typeof createApp>> = []

function mount(component: ReturnType<typeof defineComponent>) {
  const host = document.createElement('div')
  document.body.append(host)
  const app = createApp(component)
  mountedApps.push(app)
  app.mount(host)
  return host
}

afterEach(() => {
  mountedApps.splice(0).forEach((app) => app.unmount())
  document.body.replaceChildren()
})

describe('AppTwoColumnLayout responsive modes', () => {
  it.each(['fixed', 'collapsible', 'drawer', 'stack'] as const)(
    'applies the explicit %s mode contract',
    (responsiveMode) => {
      const host = mount(defineComponent({
        setup: () => () => h(
          AppTwoColumnLayout,
          { responsiveMode },
          {
            sidebar: () => h('span', 'Library'),
            default: () => h('span', 'Reader'),
          },
        ),
      }))

      const layout = host.querySelector('.app-two-column')
      expect(layout?.classList.contains(`app-two-column--mode-${responsiveMode}`)).toBe(true)
      expect(layout?.classList.contains('app-two-column--legacy')).toBe(false)
      expect(host.querySelector('.app-workbench__sidebar')).not.toBeNull()
    },
  )

  it('toggles an uncontrolled collapsible sidebar with accessible state and events', async () => {
    const updates: boolean[] = []
    const host = mount(defineComponent({
      setup: () => () => h(
        AppTwoColumnLayout,
        {
          responsiveMode: 'collapsible',
          defaultSidebarOpen: false,
          'onUpdate:sidebarOpen': (open: boolean) => updates.push(open),
        },
        {
          sidebar: () => h('span', { 'data-testid': 'sidebar-content' }, 'Library'),
          default: () => h('span', 'Reader'),
        },
      ),
    }))

    const layout = host.querySelector('.app-two-column')
    const toggle = host.querySelector<HTMLButtonElement>('.app-two-column__sidebar-toggle')
    const sidebar = host.querySelector<HTMLElement>('.app-workbench__sidebar')
    expect(layout?.classList.contains('app-two-column--sidebar-collapsed')).toBe(true)
    expect(toggle?.getAttribute('aria-expanded')).toBe('false')
    expect(toggle?.getAttribute('aria-controls')).toBe(sidebar?.id)

    toggle?.click()
    await nextTick()

    expect(layout?.classList.contains('app-two-column--sidebar-open')).toBe(true)
    expect(toggle?.getAttribute('aria-expanded')).toBe('true')
    expect(updates).toEqual([true])
    expect(host.querySelector('[data-testid="sidebar-content"]')).not.toBeNull()
  })

  it('closes an open drawer from its accessible scrim', async () => {
    const host = mount(defineComponent({
      setup: () => () => h(
        AppTwoColumnLayout,
        { responsiveMode: 'drawer' },
        {
          sidebar: () => h('span', 'Library'),
          default: () => h('span', 'Reader'),
        },
      ),
    }))

    host.querySelector<HTMLButtonElement>('.app-two-column__scrim')?.click()
    await nextTick()

    expect(host.querySelector('.app-two-column')?.classList.contains('app-two-column--sidebar-collapsed')).toBe(true)
    expect(host.querySelector('.app-two-column__scrim')).toBeNull()
  })

  it('supports scoped drawer controls when the built-in toggle header is hidden', async () => {
    const host = mount(defineComponent({
      setup: () => () => h(
        AppTwoColumnLayout,
        { responsiveMode: 'drawer', sidebarToggle: false },
        {
          sidebar: ({ close }: { close: () => void }) => h(
            'button',
            { 'data-testid': 'close-sidebar', onClick: close },
            'Close',
          ),
          default: () => h('span', 'Reader'),
        },
      ),
    }))

    expect(host.querySelector('.app-workbench__header')).toBeNull()
    expect(host.querySelector('.app-two-column')?.classList.contains('app-two-column--sidebar-open')).toBe(true)

    host.querySelector<HTMLButtonElement>('[data-testid="close-sidebar"]')?.click()
    await nextTick()

    expect(host.querySelector('.app-two-column')?.classList.contains('app-two-column--sidebar-collapsed')).toBe(true)
  })

  it('preserves legacy collapse behavior without unmounting sidebar content', async () => {
    const sidebarCollapsed = ref(false)
    const host = mount(defineComponent({
      setup: () => () => h(
        AppTwoColumnLayout,
        { sidebarAlways: true, sidebarCollapsed: sidebarCollapsed.value },
        {
          sidebar: () => h('span', { 'data-testid': 'sidebar-content' }, 'Library'),
          default: () => h('span', 'Reader'),
        },
      ),
    }))

    const layout = host.querySelector('.app-two-column')
    expect(layout?.classList.contains('app-two-column--legacy')).toBe(true)
    expect(layout?.classList.contains('app-two-column--sidebar-collapsed')).toBe(false)

    sidebarCollapsed.value = true
    await nextTick()

    expect(layout?.classList.contains('app-two-column--sidebar-collapsed')).toBe(true)
    expect(host.querySelector('[data-testid="sidebar-content"]')).not.toBeNull()
  })

  it('keeps the same main root while switching scroll ownership', async () => {
    const mainScroll = ref(true)
    const host = mount(defineComponent({
      setup: () => () => h(
        AppTwoColumnLayout,
        { mainScroll: mainScroll.value, scrollKey: 'test-main' },
        { default: () => h('span', 'Reader') },
      ),
    }))

    const root = host.querySelector<HTMLElement>('.app-two-column__main-root')
    expect(root?.dataset.routeScroll).toBe('test-main')
    expect(root?.classList.contains('app-workbench__scroll')).toBe(true)

    mainScroll.value = false
    await nextTick()

    const updatedRoot = host.querySelector<HTMLElement>('.app-two-column__main-root')
    expect(updatedRoot).toBe(root)
    expect(updatedRoot?.hasAttribute('data-route-scroll')).toBe(false)
    expect(updatedRoot?.classList.contains('app-workbench__body')).toBe(true)
  })
})
