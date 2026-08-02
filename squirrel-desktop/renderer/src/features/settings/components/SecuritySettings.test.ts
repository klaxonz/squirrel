// @vitest-environment jsdom
import { createApp, defineComponent, nextTick } from 'vue'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import SecuritySettings from './SecuritySettings.vue'

const api = vi.hoisted(() => ({
  updateUserPassword: vi.fn(),
  revokeUserSessions: vi.fn(),
}))

vi.mock('@/shared/api', () => api)
vi.mock('@/shared/icons/AppIcon.vue', () => ({
  default: defineComponent({ template: '<span aria-hidden="true" />' }),
}))
vi.mock('@/shared/components/ConfirmDialog.vue', () => ({
  default: defineComponent({ template: '<div />' }),
}))

const apps: Array<ReturnType<typeof createApp>> = []

const mountSettings = () => {
  const host = document.createElement('div')
  document.body.append(host)
  const app = createApp(SecuritySettings)
  apps.push(app)
  app.mount(host)
  return host
}

const setInput = async (input: HTMLInputElement, value: string) => {
  input.value = value
  input.dispatchEvent(new Event('input', { bubbles: true }))
  await nextTick()
}

beforeEach(() => {
  vi.clearAllMocks()
})

afterEach(() => {
  apps.splice(0).forEach((app) => app.unmount())
  document.body.replaceChildren()
})

describe('SecuritySettings password form', () => {
  it('associates every password field and supports independent reveal controls', async () => {
    const host = mountSettings()
    const current = host.querySelector<HTMLInputElement>('#security-currentPassword')!
    const next = host.querySelector<HTMLInputElement>('#security-newPassword')!

    expect(current.required).toBe(true)
    expect(current.getAttribute('aria-labelledby')).toBe('security-currentPassword-label')
    expect(current.getAttribute('aria-describedby')).toBe('security-currentPassword-description')
    expect(next.minLength).toBe(8)
    expect(next.type).toBe('password')

    host.querySelector<HTMLButtonElement>('[aria-label="显示新密码"]')!.click()
    await nextTick()
    expect(next.type).toBe('text')
    expect(current.type).toBe('password')
  })

  it('reports field-local validation errors and submits normalized valid values', async () => {
    api.updateUserPassword.mockResolvedValue(undefined)
    const host = mountSettings()
    const form = host.querySelector<HTMLFormElement>('form')!

    form.dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }))
    await nextTick()

    const current = host.querySelector<HTMLInputElement>('#security-currentPassword')!
    const next = host.querySelector<HTMLInputElement>('#security-newPassword')!
    const confirm = host.querySelector<HTMLInputElement>('#security-confirmPassword')!
    expect(current.getAttribute('aria-invalid')).toBe('true')
    expect(next.getAttribute('aria-errormessage')).toBe('security-newPassword-error')
    expect(api.updateUserPassword).not.toHaveBeenCalled()

    await setInput(current, 'old-password')
    await setInput(next, 'new-password')
    await setInput(confirm, 'new-password')
    form.dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }))
    await nextTick()
    await nextTick()

    expect(api.updateUserPassword).toHaveBeenCalledWith({
      current_password: 'old-password',
      new_password: 'new-password',
    })
  })
})
