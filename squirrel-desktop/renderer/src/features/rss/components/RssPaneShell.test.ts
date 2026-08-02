// @vitest-environment jsdom
import { createApp, defineComponent, h, nextTick, ref } from 'vue'
import { afterEach, describe, expect, it } from 'vitest'
import RssPaneShell from './RssPaneShell.vue'

const mountedApps: Array<ReturnType<typeof createApp>> = []

afterEach(() => {
  mountedApps.splice(0).forEach((app) => app.unmount())
  document.body.replaceChildren()
})

describe('RssPaneShell', () => {
  it('switches narrow pane state without remounting panes or losing scroll positions', async () => {
    const activePane = ref<'entries' | 'reader'>('entries')
    const host = document.createElement('div')
    document.body.append(host)
    const app = createApp(defineComponent({
      setup: () => () => h(
        RssPaneShell,
        { activePane: activePane.value },
        {
          entries: () => h('div', { 'data-testid': 'entries' }, 'Entries'),
          reader: () => h('div', { 'data-testid': 'reader' }, 'Reader'),
        },
      ),
    }))
    mountedApps.push(app)
    app.mount(host)

    const shell = host.querySelector('.rss-pane-shell')
    const entries = host.querySelector<HTMLElement>('[data-testid="entries"]')
    const reader = host.querySelector<HTMLElement>('[data-testid="reader"]')
    expect(shell?.classList.contains('rss-pane-shell--entries')).toBe(true)
    expect(entries).not.toBeNull()
    expect(reader).not.toBeNull()

    entries!.scrollTop = 120
    reader!.scrollTop = 340
    activePane.value = 'reader'
    await nextTick()

    expect(shell?.classList.contains('rss-pane-shell--reader')).toBe(true)
    expect(host.querySelector('[data-testid="entries"]')).toBe(entries)
    expect(host.querySelector('[data-testid="reader"]')).toBe(reader)
    expect(entries!.isConnected).toBe(true)
    expect(reader!.isConnected).toBe(true)
    expect(entries!.scrollTop).toBe(120)
    expect(reader!.scrollTop).toBe(340)
  })
})
