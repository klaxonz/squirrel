// @vitest-environment jsdom
import { createApp, defineComponent, h } from 'vue'
import { afterEach, describe, expect, it } from 'vitest'
import ToastContainer from './ToastContainer.vue'
import type { ToastItem, ToastVariant } from './useToast'

const mountedApps: Array<ReturnType<typeof createApp>> = []

const mountToast = (variant: ToastVariant) => {
  const host = document.createElement('div')
  document.body.append(host)
  const toast: ToastItem = { id: 1, variant, message: `${variant} message` }
  const app = createApp(defineComponent({
    setup: () => () => h(ToastContainer, { toast }),
  }))
  mountedApps.push(app)
  app.mount(host)
  return host.querySelector('.app-toast')!
}

afterEach(() => {
  mountedApps.splice(0).forEach((app) => app.unmount())
  document.body.replaceChildren()
})

describe('ToastContainer semantics', () => {
  it('announces errors assertively as alerts', () => {
    const toast = mountToast('error')
    expect(toast.getAttribute('role')).toBe('alert')
    expect(toast.getAttribute('aria-live')).toBe('assertive')
    expect(toast.getAttribute('aria-atomic')).toBe('true')
  })

  it.each(['success', 'info'] as const)('announces %s messages politely as statuses', (variant) => {
    const toast = mountToast(variant)
    expect(toast.getAttribute('role')).toBe('status')
    expect(toast.getAttribute('aria-live')).toBe('polite')
  })

  it('uses the info icon for neutral messages', () => {
    const toast = mountToast('info')
    const icon = toast.querySelector('.app-toast__icon')!
    expect(icon.classList.contains('lucide-info')).toBe(true)
    expect(icon.classList.contains('lucide-circle-check-big')).toBe(false)
  })
})
