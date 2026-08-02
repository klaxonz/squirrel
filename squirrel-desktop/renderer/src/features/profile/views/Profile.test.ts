// @vitest-environment jsdom
import { createApp, defineComponent, nextTick, reactive, ref } from 'vue'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import Profile from './Profile.vue'

const mocks = vi.hoisted(() => ({
  form: { nickname: 'Ada', avatar: '' },
  saving: false,
  saved: false,
  saveError: '',
  hasChanges: false,
  hydrate: vi.fn(),
  handleSave: vi.fn(),
  logout: vi.fn(),
  push: vi.fn(),
}))

vi.mock('vue-router', () => ({
  useRouter: () => ({ push: mocks.push }),
}))

vi.mock('@/shared/stores/user', () => ({
  useUserStore: () => ({
    currentUser: { nickname: 'Ada', avatar: '', created_at: '2024-01-02T00:00:00Z' },
    logout: mocks.logout,
  }),
}))

vi.mock('@/features/profile/composables/useProfileEditForm', () => ({
  useProfileEditForm: () => ({
    form: reactive(mocks.form),
    saving: ref(mocks.saving),
    saved: ref(mocks.saved),
    saveError: ref(mocks.saveError),
    hasChanges: ref(mocks.hasChanges),
    hydrate: mocks.hydrate,
    handleSave: mocks.handleSave,
  }),
}))

vi.mock('@/shared/icons/AppIcon.vue', () => ({
  default: defineComponent({ template: '<span aria-hidden="true" />' }),
}))
vi.mock('@/shared/components/layout/AppPageShell.vue', () => ({
  default: defineComponent({ template: '<div><slot /></div>' }),
}))

const mountedApps: Array<ReturnType<typeof createApp>> = []

function mountProfile() {
  const host = document.createElement('div')
  document.body.append(host)
  const app = createApp(Profile)
  mountedApps.push(app)
  app.mount(host)
  return host
}

beforeEach(() => {
  mocks.form.nickname = 'Ada'
  mocks.form.avatar = ''
  mocks.hydrate.mockReset()
  mocks.handleSave.mockReset()
  mocks.logout.mockReset()
  mocks.push.mockReset()
})

afterEach(() => {
  mountedApps.splice(0).forEach((app) => app.unmount())
  document.body.replaceChildren()
})

describe('Profile form fields', () => {
  it('associates labels, preserves the counter, and focuses the avatar field', async () => {
    const host = mountProfile()
    const nickname = host.querySelector<HTMLInputElement>('#profile-nickname')!
    const avatar = host.querySelector<HTMLInputElement>('#profile-avatar')!

    expect(nickname.getAttribute('aria-labelledby')).toBe('profile-nickname-label')
    expect(host.querySelector<HTMLLabelElement>('label[for="profile-nickname"]')?.textContent)
      .toContain('Ada'.length + '/50')
    expect(avatar.getAttribute('aria-labelledby')).toBe('profile-avatar-label')
    expect(avatar.type).toBe('url')
    expect(avatar.autocomplete).toBe('url')

    host.querySelector<HTMLButtonElement>('.profile-avatar-control')!.click()
    await nextTick()
    expect(document.activeElement).toBe(avatar)
  })

  it('references live avatar preview status and updates failure state', async () => {
    mocks.form.avatar = 'https://example.com/avatar.png'
    const host = mountProfile()
    await nextTick()

    const avatar = host.querySelector<HTMLInputElement>('#profile-avatar')!
    const description = host.querySelector<HTMLElement>('#profile-avatar-description')!
    const preview = description.querySelector<HTMLImageElement>('img')!

    expect(avatar.getAttribute('aria-describedby')).toBe(description.id)
    expect(description.textContent).toContain('图片加载成功')

    preview.dispatchEvent(new Event('error'))
    await nextTick()
    expect(description.textContent).toContain('图片加载失败，请检查链接')
  })
})
