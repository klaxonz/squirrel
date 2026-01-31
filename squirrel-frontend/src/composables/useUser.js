import { ref } from 'vue'
import { getUserById as apiGetUserById, getUserMe, loginUser, registerUser, updateUserMe } from '@/api'
import { clearAuthStorage } from '../utils/auth'

const currentUser = ref(null)
const isAuthenticated = ref(false)
const loading = ref(false)
const error = ref(null)

export function useUser() {
  const register = async (data) => {
    loading.value = true
    error.value = null

    const result = await registerUser(data)

    loading.value = false
    error.value = result.error
    return result
  }

  const login = async (data) => {
    loading.value = true
    error.value = null

    const result = await loginUser(data)

    if (!result.error && result.data?.access_token) {
      localStorage.setItem('token', result.data.access_token)
      currentUser.value = result.data.user || null
      isAuthenticated.value = true
    }

    loading.value = false
    error.value = result.error
    return result
  }

  const logout = () => {
    clearAuthStorage()
    currentUser.value = null
    isAuthenticated.value = false
  }

  const getCurrentUser = async () => {
    if (!localStorage.getItem('token')) {
      isAuthenticated.value = false
      currentUser.value = null
      error.value = null
      return { data: null, error: null }
    }

    loading.value = true
    error.value = null

    const result = await getUserMe()

    if (result.error?.status === 401) {
      logout()
    } else if (!result.error) {
      currentUser.value = result.data || null
      isAuthenticated.value = true
    }

    loading.value = false
    error.value = result.error
    return result
  }

  const updateProfile = async (data) => {
    loading.value = true
    error.value = null

    const result = await updateUserMe(data)

    if (!result.error) {
      currentUser.value = result.data || null
    }

    loading.value = false
    error.value = result.error
    return result
  }

  const getUserById = async (userId) => {
    loading.value = true
    error.value = null

    const result = await apiGetUserById(userId)

    loading.value = false
    error.value = result.error
    return result
  }

  return {
    currentUser,
    isAuthenticated,
    loading,
    error,
    register,
    login,
    logout,
    getCurrentUser,
    updateProfile,
    getUserById
  };
}
