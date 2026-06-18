import { defineStore } from 'pinia'
import { ref } from 'vue'
import { getUserMe, loginUser, logoutUser, registerUser, updateUserMe } from '@/api'
import { clearAuthStorage } from '@/utils/auth'
import type { User } from '@/types/user'

export type { User }

export const useUserStore = defineStore('user', () => {
  const currentUser = ref<User | null>(null)
  const isAuthenticated = ref(false)
  const hasResolvedAuth = ref(false)
  const loading = ref(false)
  // ponytail: dropped a dead `error` ref — it was declared and exported but
  // never written (all actions `return response` without setting it), so it
  // only ever exposed a perpetual null to consumers.

  const clearState = () => {
    clearAuthStorage()
    currentUser.value = null
    isAuthenticated.value = false
    hasResolvedAuth.value = true
  }

  const fetchCurrentUser = async () => {
    loading.value = true
    const response = await getUserMe()
    if (response.error?.status === 401) {
      clearState()
    } else if (!response.error) {
      currentUser.value = (response.data as User | null) || null
      isAuthenticated.value = !!response.data
    }
    hasResolvedAuth.value = true
    loading.value = false
    return response
  }

  const login = async (credentials: Record<string, unknown>) => {
    loading.value = true
    const response = await loginUser(credentials)
    if (!response.error) {
      currentUser.value = (response.data as User | null) || null
      isAuthenticated.value = true
      hasResolvedAuth.value = true
    }
    loading.value = false
    return response
  }

  const register = async (payload: Record<string, unknown>) => {
    loading.value = true
    const response = await registerUser(payload)
    loading.value = false
    return response
  }

  const logout = async () => {
    await logoutUser()
    clearState()
  }

  const updateProfile = async (profile: Record<string, unknown>) => {
    loading.value = true
    const response = await updateUserMe(profile)
    if (!response.error) {
      currentUser.value = (response.data as User | null) || null
    }
    loading.value = false
    return response
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
