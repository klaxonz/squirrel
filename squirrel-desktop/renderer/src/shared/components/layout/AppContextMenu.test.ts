// @vitest-environment jsdom
import { createApp, defineComponent, h, nextTick, ref } from 'vue'
import { afterEach, describe, expect, it } from 'vitest'
import AppContextMenu from './AppContextMenu.vue'

const mountedApps: Array<ReturnType<typeof createApp>> = []

afterEach(() => {
  mountedApps.splice(0).forEach((app) => app.unmount())
  document.body.replaceChildren()
})

describe('AppContextMenu focus lifecycle', () => {
  it('restores focus when an open menu is unmounted', async () => {
    const menuMounted = ref(false)
    const trigger = ref<HTMLElement | null>(null)
    const TestHost = defineComponent({
      setup() {
        return () => h('div', [
          h('button', { ref: trigger }, 'Open menu'),
          menuMounted.value
            ? h(
                AppContextMenu,
                {
                  visible: true,
                  label: 'Actions',
                  position: { x: 0, y: 0 },
                },
                { default: () => h('button', { role: 'menuitem', tabindex: -1 }, 'Action') },
              )
            : null,
        ])
      },
    })
    const host = document.createElement('div')
    document.body.append(host)
    const app = createApp(TestHost)
    mountedApps.push(app)
    app.mount(host)

    trigger.value?.focus()
    menuMounted.value = true
    await nextTick()
    await nextTick()
    expect(document.activeElement?.getAttribute('role')).toBe('menuitem')

    menuMounted.value = false
    await nextTick()
    expect(document.activeElement).toBe(trigger.value)
  })
})
