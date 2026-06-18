import { ref } from 'vue'
import { getUserMe, loginUser, logoutUser, registerUser, updateUserMe } from '@/api'
import { clearAuthStorage } from '@/utils/auth'
import type { ApiResult } from '@/types/api'

type User = Record<string, unknown>

const currentUser = ref<User | null>(null)
const isAuthenticated = ref(false)
const hasResolvedAuth = ref(false)
const loading = ref(false)
const error = ref<unknown>(null)

const clearUserState = () => {
  clearAuthStorage()
  currentUser.value = null
  isAuthenticated.value = false
  hasResolvedAuth.value = true
}

export function useUser() {
  const register = async (payload: Record<string, unknown>) => {
    loading.value = true
    error.value = null

    const response = (await registerUser(payload)) as ApiResult<User>

    loading.value = false
    error.value = response.error
    return response
  }

  const login = async (credentials: Record<string, unknown>) => {
    loading.value = true
    error.value = null

    const response = (await loginUser(credentials)) as ApiResult<User>

    if (!response.error) {
      currentUser.value = response.data || null
      isAuthenticated.value = !!response.data
      hasResolvedAuth.value = true
    }

    loading.value = false
    error.value = response.error
    return response
  }

  const logout = async () => {
    loading.value = true
    error.value = null

    const response = (await logoutUser()) as ApiResult<null>
    clearUserState()

    loading.value = false
    error.value = response.error
    return response
  }

  const getCurrentUser = async () => {
    loading.value = true
    error.value = null

    const response = (await getUserMe()) as ApiResult<User>

    if ((response.error as { status?: number } | null)?.status === 401) {
      clearUserState()
    } else if (!response.error) {
      currentUser.value = response.data || null
      isAuthenticated.value = true
      hasResolvedAuth.value = true
    } else {
      currentUser.value = null
      isAuthenticated.value = false
      hasResolvedAuth.value = true
    }

    loading.value = false
    error.value = response.error
    return response
  }

  const updateProfile = async (profile: Record<string, unknown>) => {
    loading.value = true
    error.value = null

    const response = (await updateUserMe(profile)) as ApiResult<User>

    if (!response.error) {
      currentUser.value = response.data || null
    }

    loading.value = false
    error.value = response.error
    return response
  }

  return {
    currentUser,
    isAuthenticated,
    hasResolvedAuth,
    loading,
    error,
    register,
    login,
    logout,
    getCurrentUser,
    updateProfile
  }
}
