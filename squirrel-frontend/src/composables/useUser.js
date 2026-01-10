import { ref } from 'vue'
import axios from '../utils/axios'

// 创建全局状态
const currentUser = ref(null)
const isAuthenticated = ref(false)
const loading = ref(false)
const error = ref(null)

// API 响应处理工具函数
const handleApiResponse = (response) => {
  if (response.data.code !== 0) {
    throw new Error(response.data.msg)
  }
  return response.data
}

const handleApiError = (err, defaultMessage) => {
  if (err.response?.data) {
    const errorMessage = err.response.data.msg || err.response.data.detail
    error.value = errorMessage
    throw new Error(errorMessage)
  }
  error.value = err.message || defaultMessage
  throw err
}

// 通用的API调用包装器
const apiCall = async (apiFn, options = {}) => {
  const { defaultErrorMessage = '操作失败', skipLoading = false } = options

  if (!skipLoading) loading.value = true
  error.value = null

  try {
    const response = await apiFn()
    return handleApiResponse(response)
  } catch (err) {
    handleApiError(err, defaultErrorMessage)
  } finally {
    if (!skipLoading) loading.value = false
  }
}

export function useUser() {
  const register = async (data) => {
    return apiCall(
      () => axios.post('/api/users/register', data),
      { defaultErrorMessage: '注册失败' }
    )
  }

  const login = async (data) => {
    const result = await apiCall(
      () => axios.post('/api/users/login', data),
      { defaultErrorMessage: '登录失败' }
    )
    currentUser.value = result.data.user
    isAuthenticated.value = true
    return result
  }

  const logout = () => {
    localStorage.removeItem('token')
    localStorage.removeItem('user')
    currentUser.value = null
    isAuthenticated.value = false
  }

  const getCurrentUser = async () => {
    if (!localStorage.getItem('token')) {
      isAuthenticated.value = false
      currentUser.value = null
      return null
    }

    try {
      const result = await apiCall(
        () => axios.get('/api/users/me'),
        { defaultErrorMessage: '获取用户信息失败' }
      )
      currentUser.value = result.data
      isAuthenticated.value = true
      return result
    } catch (err) {
      if (err.response?.status === 401) {
        logout()
      }
      throw err
    }
  }

  const updateProfile = async (data) => {
    const result = await apiCall(
      () => axios.put('/api/users/me', data),
      { defaultErrorMessage: '更新用户信息失败' }
    )
    currentUser.value = result
    return result
  }

  const getUserById = async (userId) => {
    return apiCall(
      () => axios.get(`/api/users/${userId}`),
      { defaultErrorMessage: '获取用户信息失败' }
    )
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