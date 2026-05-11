import { defineStore } from 'pinia'
import { ref } from 'vue'
import { getUserMe, loginUser, logoutUser, registerUser, updateUserMe } from '@/api'
import { clearAuthStorage } from '@/utils/auth'

export type User = Record<string, any>

export const useUserStore = defineStore('user', () => {
  const currentUser = ref<User | null>(null)
  const isAuthenticated = ref(false)
  const hasResolvedAuth = ref(false)
  const loading = ref(false)
  const error = ref<any>(null)

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
      currentUser.value = result.data || null
      isAuthenticated.value = !!result.data
    }
    hasResolvedAuth.value = true
    loading.value = false
    return result
  }

  const login = async (data: any) => {
    loading.value = true
    const result = await loginUser(data)
    if (!result.error) {
      currentUser.value = result.data || null
      isAuthenticated.value = true
      hasResolvedAuth.value = true
    }
    loading.value = false
    return result
  }

  const register = async (data: any) => {
    loading.value = true
    const result = await registerUser(data)
    loading.value = false
    return result
  }

  const logout = async () => {
    await logoutUser()
    clearState()
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
    clearState
  }
})
