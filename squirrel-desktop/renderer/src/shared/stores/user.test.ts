// @vitest-environment jsdom

import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { logoutAndRedirect } from '@/shared/lib/auth'
import { useUserStore } from './user'

const stopMediaOnAuthInvalidation = vi.fn()

vi.mock('@/shared/lib/stopMediaOnAuthInvalidation', () => ({
  stopMediaOnAuthInvalidation: (...args: unknown[]) => stopMediaOnAuthInvalidation(...args),
}))

describe('user auth invalidation', () => {
  beforeEach(() => {
    vi.stubGlobal('localStorage', {
      getItem: vi.fn(),
      setItem: vi.fn(),
      removeItem: vi.fn(),
    })
    setActivePinia(createPinia())
    stopMediaOnAuthInvalidation.mockReset()
  })

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
    expect(stopMediaOnAuthInvalidation).toHaveBeenCalledOnce()
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
