// @vitest-environment jsdom

import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { ApiError } from '@/shared/lib/apiError'
import { logoutAndRedirect } from '@/shared/lib/auth'
import { getUserMe, loginUser, registerUser, updateUserMe } from '@/shared/api'
import { useUserStore } from './user'

vi.mock('@/shared/api', () => ({
  getUserMe: vi.fn(),
  loginUser: vi.fn(),
  logoutUser: vi.fn(),
  registerUser: vi.fn(),
  updateUserMe: vi.fn(),
}))

const mockedGetUserMe = vi.mocked(getUserMe)
const mockedLoginUser = vi.mocked(loginUser)
const mockedRegisterUser = vi.mocked(registerUser)
const mockedUpdateUserMe = vi.mocked(updateUserMe)

const stopMediaOnAuthInvalidation = vi.fn()

vi.mock('@/shared/lib/stopMediaOnAuthInvalidation', () => ({
  stopMediaOnAuthInvalidation: (...args: unknown[]) => stopMediaOnAuthInvalidation(...args),
}))

beforeEach(() => {
  vi.stubGlobal('localStorage', {
    getItem: vi.fn(),
    setItem: vi.fn(),
    removeItem: vi.fn(),
  })
  setActivePinia(createPinia())
  mockedGetUserMe.mockReset()
  mockedLoginUser.mockReset()
  mockedRegisterUser.mockReset()
  mockedUpdateUserMe.mockReset()
  mockedGetUserMe.mockResolvedValue(null as never)
  mockedLoginUser.mockResolvedValue(null as never)
  mockedRegisterUser.mockResolvedValue(null as never)
  mockedUpdateUserMe.mockResolvedValue(null as never)
  stopMediaOnAuthInvalidation.mockReset()
})

describe('user auth actions', () => {
  it('rejects business errors from login without returning a tuple', async () => {
    const error = new ApiError('邮箱或密码错误', 'API', 400)
    mockedLoginUser.mockRejectedValue(error)

    await expect(useUserStore().login({ email: 'a', password: 'b' })).rejects.toBe(error)
  })

  it('rejects network errors from register', async () => {
    const error = new Error('网络异常')
    mockedRegisterUser.mockRejectedValue(error)

    await expect(useUserStore().register({ email: 'a' })).rejects.toBe(error)
  })

  it('rejects 401 from current-user lookup and clears auth state', async () => {
    const store = useUserStore()
    store.$patch({ currentUser: { id: 1, nickname: 'a', avatar: null, created_at: '', updated_at: '' }, isAuthenticated: true })
    const error = new ApiError('未授权', 'UNAUTHORIZED', 401)
    mockedGetUserMe.mockRejectedValue(error)

    await expect(store.fetchCurrentUser()).rejects.toBe(error)
    expect(store.currentUser).toBeNull()
    expect(store.isAuthenticated).toBe(false)
    expect(stopMediaOnAuthInvalidation).toHaveBeenCalledOnce()
  })

  it('rejects profile update errors', async () => {
    const error = new ApiError('保存失败', 'API', 400)
    mockedUpdateUserMe.mockRejectedValue(error)

    await expect(useUserStore().updateProfile({ nickname: 'new' })).rejects.toBe(error)
  })
})

describe('user auth invalidation', () => {
  it('clears the live Pinia session before the router handles a 401 redirect', async () => {
    const store = useUserStore()
    store.$patch({
      currentUser: { id: 1, nickname: 'klaxon', avatar: null, created_at: '', updated_at: '' },
      isAuthenticated: true,
      hasResolvedAuth: true,
    })

    window.location.hash = '#/home'
    await logoutAndRedirect()

    expect(store.currentUser).toBeNull()
    expect(store.isAuthenticated).toBe(false)
    expect(store.hasResolvedAuth).toBe(true)
    expect(window.location.hash).toBe('#/login')
    expect(stopMediaOnAuthInvalidation).toHaveBeenCalled()
  })

  it('stops media when the user explicitly logs out', async () => {
    const store = useUserStore()
    store.$patch({
      currentUser: { id: 1, nickname: 'klaxon', avatar: null, created_at: '', updated_at: '' },
      isAuthenticated: true,
      hasResolvedAuth: true,
    })

    await store.logout()

    expect(store.isAuthenticated).toBe(false)
    expect(stopMediaOnAuthInvalidation).toHaveBeenCalledOnce()
  })
})
