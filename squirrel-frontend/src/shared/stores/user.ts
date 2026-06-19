import { defineStore } from 'pinia'
import { ref } from 'vue'
import { getUserMe, loginUser, logoutUser, registerUser, updateUserMe } from '@/shared/api'
import { clearAuthStorage } from '@/shared/lib/auth'
import { isApiError } from '@/shared/lib/apiError'
import type { User } from '@/shared/types/user'

export type { User }

// ponytail: the store still owns client-side auth state (currentUser /
// isAuthenticated / hasResolvedAuth) + the logout side-effect (clears cookies,
// redirects). API errors now surface as thrown ApiError — the load/login/register
// actions re-shape them into the legacy `{ data, error }` return tuple so the
// existing callers (Login/Register/Profile, which render inline field errors) keep
// working without a broader rewrite. The error here is `ApiError | null`.
type ResultTuple<T> = { data: T | null; error: unknown | null }

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
  }

  const fetchCurrentUser = async (): Promise<ResultTuple<User>> => {
    loading.value = true
    try {
      const data = await getUserMe() as User | null
      currentUser.value = data || null
      isAuthenticated.value = !!data
      hasResolvedAuth.value = true
      return { data, error: null }
    } catch (error) {
      // 401 means the session is gone — clear local auth so the router redirects
      // to login. Other errors just leave the user unresolved-but-not-logged-out.
      if (isApiError(error) && error.type === 'UNAUTHORIZED') {
        clearState()
      } else {
        hasResolvedAuth.value = true
      }
      return { data: null, error }
    } finally {
      loading.value = false
    }
  }

  const login = async (credentials: Record<string, unknown>): Promise<ResultTuple<User>> => {
    loading.value = true
    try {
      const data = await loginUser(credentials) as User | null
      currentUser.value = data || null
      isAuthenticated.value = true
      hasResolvedAuth.value = true
      return { data, error: null }
    } catch (error) {
      return { data: null, error }
    } finally {
      loading.value = false
    }
  }

  const register = async (payload: Record<string, unknown>): Promise<ResultTuple<unknown>> => {
    loading.value = true
    try {
      const data = await registerUser(payload)
      return { data, error: null }
    } catch (error) {
      return { data: null, error }
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
  }

  const updateProfile = async (profile: Record<string, unknown>): Promise<ResultTuple<User>> => {
    loading.value = true
    try {
      const data = await updateUserMe(profile) as User | null
      currentUser.value = data || null
      return { data, error: null }
    } catch (error) {
      return { data: null, error }
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
