import { get, post, put } from '@/utils/request'

export const registerUser = async (payload) => {
  return post('/api/users/register', payload)
}

export const loginUser = async (payload) => {
  return post('/api/users/login', payload)
}

export const getUserMe = async () => {
  return get('/api/users/me')
}

export const updateUserMe = async (payload) => {
  return put('/api/users/me', payload)
}

export const getUserById = async (userId) => {
  return get(`/api/users/${userId}`)
}

export const getUserMeConfig = async () => {
  return get('/api/users/me/config')
}

export const updateUserMeConfig = async (payload) => {
  return put('/api/users/me/config', payload)
}

