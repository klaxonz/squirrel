import { get, post, put } from '@/utils/request'

export const registerUser = async (payload: Record<string, unknown>) => {
  return post('/api/users/register', payload)
}

export const loginUser = async (payload: Record<string, unknown>) => {
  return post('/api/users/login', payload)
}

export const logoutUser = async () => {
  return post('/api/users/logout')
}

export const getUserMe = async () => {
  return get('/api/users/me')
}

export const updateUserMe = async (payload: Record<string, unknown>) => {
  return put('/api/users/me', payload)
}

export const getUserMeConfig = async () => {
  return get('/api/users/me/config')
}

export const updateUserMeConfig = async (payload: Record<string, unknown>) => {
  return put('/api/users/me/config', payload)
}
