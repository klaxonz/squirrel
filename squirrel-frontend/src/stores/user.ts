import { defineStore } from 'pinia'
import { ref } from 'vue'
import { getUserMe, loginUser, logoutUser, registerUser, updateUserMe } from '@/api'
import { clearAuthStorage } from '@/utils/auth'

export interface User {
  id?: number | string
  nickname?: string
  email?: string
  avatar?: string
  created_at?: string
  [key: string]: unknown
}

interface ApiError {
  status?: number
  message?: string
  [key: string]: unknown
}

export const useUserStore = defineStore('user', () => {
  const currentUser = ref<User | null>(null)
  const isAuthenticated = ref(false)
  const hasResolvedAuth = ref(false)
  const loading = ref(false)
  const error = ref<ApiError | null>(null)

  const clearState = () => {
    clearAuthStorage()
    currentUser.value = null
    isAuthenticated.value = false
    hasResolvedAuth.value = true
  }

  const fetchCurrentUser = async () => {
    loading.value = true
    const result = await getUserMe()
    if (result.error?.status === 401) {
      clearState()
    } else if (!result.error) {
      currentUser.value = (result.data as User | null) || null
      isAuthenticated.value = !!result.data
    }
    hasResolvedAuth.value = true
    loading.value = false
    return result
  }

  const login = async (data: Record<string, unknown>) => {
    loading.value = true
    const result = await loginUser(data)
    if (!result.error) {
      currentUser.value = (result.data as User | null) || null
      isAuthenticated.value = true
      hasResolvedAuth.value = true
    }
    loading.value = false
    return result
  }

  const register = async (data: Record<string, unknown>) => {
    loading.value = true
    const result = await registerUser(data)
    loading.value = false
    return result
  }

  const logout = async () => {
    await logoutUser()
    clearState()
  }

  const updateProfile = async (data: Record<string, unknown>) => {
    loading.value = true
    const result = await updateUserMe(data)
    if (!result.error) {
      currentUser.value = (result.data as User | null) || null
    }
    loading.value = false
    return result
  }

  return {
    currentUser,
    isAuthenticated,
    hasResolvedAuth,
    loading,
    error,
    fetchCurrentUser,
    login,
    register,
    logout,
    updateProfile,
    clearState
  }
})
