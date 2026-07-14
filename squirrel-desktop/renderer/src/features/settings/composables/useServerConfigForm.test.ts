import { nextTick } from 'vue'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { useServerConfigForm } from './useServerConfigForm'

const mocks = vi.hoisted(() => ({
  serverUrl: { value: 'http://127.0.0.1:8001' },
  setServerUrl: vi.fn(),
  testServerConnection: vi.fn(),
  logoutAndRedirect: vi.fn(),
  toastError: vi.fn(),
}))

vi.mock('@/shared/composables/useServerConfig', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/shared/composables/useServerConfig')>()
  return {
    ...actual,
    useServerConfig: () => ({
      serverUrl: mocks.serverUrl,
      setServerUrl: mocks.setServerUrl,
      testServerConnection: mocks.testServerConnection,
    }),
  }
})

vi.mock('@/shared/components/toast/useToast', () => ({
  useToast: () => ({
    error: mocks.toastError,
  }),
}))

vi.mock('@/shared/lib/auth', () => ({
  logoutAndRedirect: mocks.logoutAndRedirect,
}))

describe('server config switching', () => {
  beforeEach(() => {
    mocks.serverUrl.value = 'http://127.0.0.1:8001'
    mocks.setServerUrl.mockReset()
    mocks.setServerUrl.mockResolvedValue(true)
    mocks.testServerConnection.mockReset()
    mocks.testServerConnection.mockResolvedValue({ ok: true, message: '连接成功' })
    mocks.logoutAndRedirect.mockReset()
    mocks.logoutAndRedirect.mockResolvedValue(undefined)
    mocks.toastError.mockReset()
  })

  it('tests, persists, and reloads when switching to another server', async () => {
    const form = useServerConfigForm()
    form.serverForm.value.url = 'http://192.168.1.8:9000/path'

    expect(form.canSwitchServer.value).toBe(true)

    await form.handleSwitchServer()

    expect(mocks.testServerConnection).toHaveBeenCalledWith('http://192.168.1.8:9000')
    expect(mocks.setServerUrl).toHaveBeenCalledWith('http://192.168.1.8:9000')
    expect(mocks.logoutAndRedirect).toHaveBeenCalledOnce()
  })

  it('does not persist an unreachable target server', async () => {
    mocks.testServerConnection.mockResolvedValue({
      ok: false,
      message: '无法连接到服务器',
    })

    const form = useServerConfigForm()
    form.serverForm.value.url = 'http://192.168.1.9:9000'

    await form.handleSwitchServer()

    expect(form.serverTestResult.value).toBe(false)
    expect(mocks.setServerUrl).not.toHaveBeenCalled()
    expect(mocks.logoutAndRedirect).not.toHaveBeenCalled()
    expect(mocks.toastError).toHaveBeenCalledWith('无法连接到服务器')
  })

  it('reuses a successful test only while the target URL is unchanged', async () => {
    const form = useServerConfigForm()
    form.serverForm.value.url = 'http://192.168.1.8:9000'

    await form.handleTestServer()
    expect(form.serverTestResult.value).toBe(true)

    form.serverForm.value.url = 'http://192.168.1.10:9000'
    await nextTick()

    expect(form.serverTestResult.value).toBeNull()

    await form.handleSwitchServer()
    expect(mocks.testServerConnection).toHaveBeenCalledTimes(2)
  })

  it('disables switching when the normalized address is unchanged or invalid', () => {
    const form = useServerConfigForm()

    form.serverForm.value.url = 'http://127.0.0.1:8001/'
    expect(form.canSwitchServer.value).toBe(false)

    form.serverForm.value.url = 'not-a-url'
    expect(form.canSwitchServer.value).toBe(false)
  })
})
