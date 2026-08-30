import { defineStore } from 'pinia'
import { onScopeDispose, ref } from 'vue'
import { getUserMe, loginUser, logoutUser, registerUser, updateUserMe } from '@/shared/api'
import { clearAuthStorage, subscribeToAuthInvalidation } from '@/shared/lib/auth'
import { isApiError } from '@/shared/lib/apiError'
import { resetReactive as resetNavigationHistory } from '@/shared/lib/navigationHistory'
import { stopMediaOnAuthInvalidation } from '@/shared/lib/stopMediaOnAuthInvalidation'
import type { User } from '@/shared/types/user'

export type { User }

// The store owns client-side auth state and logout/invalidation side effects.
// API failures remain ApiError exceptions so callers can render them inline.

export const useUserStore = defineStore('user', () => {
  const currentUser = ref<User | null>(null)
  const isAuthenticated = ref(false)
  const hasResolvedAuth = ref(false)
  const loading = ref(false)

  const clearState = () => {
    clearAuthStorage()
    currentUser.value = null
    isAuthenticated.value = false
    hasResolvedAuth.value = true
    // Auth boundary: stop video/music immediately so logout cannot leave media
    // playing after AppLayout tears down (or while PiP would retain the session).
    stopMediaOnAuthInvalidation()
  }

  const unsubscribeAuthInvalidation = subscribeToAuthInvalidation(clearState)
  onScopeDispose(unsubscribeAuthInvalidation)

  const fetchCurrentUser = async (): Promise<User | null> => {
    loading.value = true
    try {
      const data = await getUserMe() as User | null
      currentUser.value = data || null
      isAuthenticated.value = !!data
      hasResolvedAuth.value = true
      return data
    } catch (error) {
      // 401 means the session is gone — clear local auth so the router redirects
      // to login. Other errors still resolve auth initialization before bubbling.
      if (isApiError(error) && error.type === 'UNAUTHORIZED') {
        clearState()
      } else {
        hasResolvedAuth.value = true
      }
      throw error
    } finally {
      loading.value = false
    }
  }

  const login = async (credentials: Record<string, unknown>): Promise<User | null> => {
    loading.value = true
    try {
      const data = await loginUser(credentials) as User | null
      currentUser.value = data || null
      isAuthenticated.value = true
      hasResolvedAuth.value = true
      return data
    } finally {
      loading.value = false
    }
  }

  const register = async (payload: Record<string, unknown>): Promise<unknown> => {
    loading.value = true
    try {
      return await registerUser(payload)
    } finally {
      loading.value = false
    }
  }

  const logout = async () => {
    try {
      await logoutUser()
    } catch {
      // logout best-effort — clear local state regardless
    }
    clearState()
    // 登出后清空应用层历史栈，避免下一个账号能"前进"到上一个账号浏览过的页面。
    resetNavigationHistory()
  }

  const updateProfile = async (profile: Record<string, unknown>): Promise<User | null> => {
    loading.value = true
    try {
      const data = await updateUserMe(profile) as User | null
      currentUser.value = data || null
      return data
    } finally {
      loading.value = false
    }
  }

  return {
    currentUser,
    isAuthenticated,
    hasResolvedAuth,
    loading,
    fetchCurrentUser,
    login,
    register,
    logout,
    updateProfile,
    clearState
  }
})
