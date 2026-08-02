// @vitest-environment jsdom
import { createApp, defineComponent, nextTick } from 'vue'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import Login from './Login.vue'
import Register from './Register.vue'

const mocks = vi.hoisted(() => ({
  login: vi.fn(),
  register: vi.fn(),
  push: vi.fn(),
}))

vi.mock('vue-router', () => ({
  useRouter: () => ({ push: mocks.push }),
}))

vi.mock('@/shared/stores/user', () => ({
  useUserStore: () => ({ login: mocks.login, register: mocks.register }),
}))

vi.mock('@/shared/lib/navigationHistory', () => ({ resetReactive: vi.fn() }))
vi.mock('@/shared/icons/AppIcon.vue', () => ({
  default: defineComponent({ template: '<span aria-hidden="true" />' }),
}))
vi.mock('@/features/auth/components/AuthEntryCard.vue', () => ({
  default: defineComponent({
    template: '<div><slot /><slot name="footer" /></div>',
  }),
}))

const mountedApps: Array<ReturnType<typeof createApp>> = []

function mount(component: typeof Login | typeof Register) {
  const host = document.createElement('div')
  document.body.append(host)
  const app = createApp(component)
  app.component('router-link', defineComponent({ template: '<a><slot /></a>' }))
  mountedApps.push(app)
  app.mount(host)
  return host
}

beforeEach(() => {
  mocks.login.mockReset()
  mocks.register.mockReset()
  mocks.push.mockReset()
})

afterEach(() => {
  mountedApps.splice(0).forEach((app) => app.unmount())
  document.body.replaceChildren()
})

describe('auth form fields', () => {
  it('associates login labels and preserves password reveal and remember-me behavior', async () => {
    const host = mount(Login)
    const email = host.querySelector<HTMLInputElement>('#email')!
    const password = host.querySelector<HTMLInputElement>('#password')!
    const rememberMe = host.querySelector<HTMLInputElement>('#rememberMe')!

    expect(host.querySelector<HTMLLabelElement>('label[for="email"]')?.id)
      .toBe(email.getAttribute('aria-labelledby'))
    expect(host.querySelector<HTMLLabelElement>('label[for="password"]')?.id)
      .toBe(password.getAttribute('aria-labelledby'))
    expect(email.required).toBe(true)
    expect(email.autocomplete).toBe('email')
    expect(password.required).toBe(true)
    expect(password.autocomplete).toBe('current-password')
    expect(password.type).toBe('password')

    host.querySelector<HTMLButtonElement>('[aria-label="显示密码"]')!.click()
    await nextTick()
    expect(password.type).toBe('text')
    expect(host.querySelector('[aria-label="隐藏密码"]')).not.toBeNull()

    expect(rememberMe.type).toBe('checkbox')
    rememberMe.click()
    await nextTick()
    expect(rememberMe.checked).toBe(true)
  })

  it('associates registration fields and references the password description', async () => {
    const host = mount(Register)
    const nickname = host.querySelector<HTMLInputElement>('#nickname')!
    const email = host.querySelector<HTMLInputElement>('#email')!
    const password = host.querySelector<HTMLInputElement>('#password')!
    const description = host.querySelector<HTMLElement>('#password-description')!

    for (const input of [nickname, email, password]) {
      const label = host.querySelector<HTMLLabelElement>(`label[for="${input.id}"]`)!
      expect(input.getAttribute('aria-labelledby')).toBe(label.id)
      expect(input.required).toBe(true)
    }
    expect(nickname.autocomplete).toBe('nickname')
    expect(email.autocomplete).toBe('email')
    expect(password.autocomplete).toBe('new-password')
    expect(password.minLength).toBe(8)
    expect(password.getAttribute('aria-describedby')).toBe(description.id)
    expect(description.textContent).toContain('至少 8 个字符')

    host.querySelector<HTMLButtonElement>('[aria-label="显示密码"]')!.click()
    await nextTick()
    expect(password.type).toBe('text')
  })
})
