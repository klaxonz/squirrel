import { get, post, put } from '@/utils/request'
import type { User, UserConfig } from '@/types/user'

export const registerUser = async (payload: Record<string, unknown>) => {
  return post<User>('/api/users/register', payload)
}

export const loginUser = async (payload: Record<string, unknown>) => {
  return post<User>('/api/users/login', payload)
}

export const logoutUser = async () => {
  return post('/api/users/logout')
}

export const getUserMe = async () => {
  return get<User>('/api/users/me')
}

export const updateUserMe = async (payload: Record<string, unknown>) => {
  return put<User>('/api/users/me', payload)
}

export const updateUserPassword = async (payload: Record<string, unknown>) => {
  return put('/api/users/me/password', payload)
}

export const revokeUserSessions = async () => {
  return post('/api/users/me/revoke-sessions')
}

export const getUserMeConfig = async () => {
  return get<UserConfig>('/api/users/me/config')
}

export const updateUserMeConfig = async (payload: Record<string, unknown>) => {
  return put<UserConfig>('/api/users/me/config', payload)
}
