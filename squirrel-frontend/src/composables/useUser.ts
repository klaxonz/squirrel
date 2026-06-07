import { ref } from 'vue'
import { getUserMe, loginUser, logoutUser, registerUser, updateUserMe } from '@/api'
import { clearAuthStorage } from '@/utils/auth'
import type { ApiResult } from '@/types/api'

type User = Record<string, unknown>

const currentUser = ref<User | null>(null)
const isAuthenticated = ref(false)
const hasResolvedAuth = ref(false)
const loading = ref(false)
const error = ref<any>(null)

const clearUserState = () => {
  clearAuthStorage()
  currentUser.value = null
  isAuthenticated.value = false
  hasResolvedAuth.value = true
}

export function useUser() {
  const register = async (data: Record<string, unknown>) => {
    loading.value = true
    error.value = null

    const result = (await registerUser(data)) as ApiResult<User>

    loading.value = false
    error.value = result.error
    return result
  }

  const login = async (data: Record<string, unknown>) => {
    loading.value = true
    error.value = null

    const result = (await loginUser(data)) as ApiResult<User>

    if (!result.error) {
      currentUser.value = result.data || null
      isAuthenticated.value = !!result.data
      hasResolvedAuth.value = true
    }

    loading.value = false
    error.value = result.error
    return result
  }

  const logout = async () => {
    loading.value = true
    error.value = null

    const result = (await logoutUser()) as ApiResult<null>
    clearUserState()

    loading.value = false
    error.value = result.error
    return result
  }

  const getCurrentUser = async () => {
    loading.value = true
    error.value = null

    const result = (await getUserMe()) as ApiResult<User>

    if ((result.error as { status?: number } | null)?.status === 401) {
      clearUserState()
    } else if (!result.error) {
      currentUser.value = result.data || null
      isAuthenticated.value = true
      hasResolvedAuth.value = true
    } else {
      currentUser.value = null
      isAuthenticated.value = false
      hasResolvedAuth.value = true
    }

    loading.value = false
    error.value = result.error
    return result
  }

  const updateProfile = async (data: Record<string, unknown>) => {
    loading.value = true
    error.value = null

    const result = (await updateUserMe(data)) as ApiResult<User>

    if (!result.error) {
      currentUser.value = result.data || null
    }

    loading.value = false
    error.value = result.error
    return result
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
