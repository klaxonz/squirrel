import { ref } from 'vue'
import { getUserById as apiGetUserById, getUserMe, loginUser, registerUser, updateUserMe } from '@/api'
import { clearAuthStorage } from '@/utils/auth'

type User = Record<string, unknown>
type ApiResult<T> = { data?: T | null; error?: any }
type AuthResult = { access_token?: string; user?: User }

const currentUser = ref<User | null>(null)
const isAuthenticated = ref(false)
const loading = ref(false)
const error = ref<any>(null)

export function useUser() {
  const register = async (data: Record<string, unknown>) => {
    loading.value = true
    error.value = null

    const result = (await registerUser(data)) as ApiResult<AuthResult>

    loading.value = false
    error.value = result.error
    return result
  }

  const login = async (data: Record<string, unknown>) => {
    loading.value = true
    error.value = null

    const result = (await loginUser(data)) as ApiResult<AuthResult>

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

    const result = (await getUserMe()) as ApiResult<User>

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

  const getUserById = async (userId: string | number) => {
    loading.value = true
    error.value = null

    const result = (await apiGetUserById(userId)) as ApiResult<User>

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
