import { get, post } from '@/utils/request'

export const getSystemConfig = async () => {
  return get<Record<string, unknown>>('/api/system/config')
}

export const saveSystemConfig = async (payload: Record<string, unknown> = {}) => {
  return post<Record<string, unknown>>('/api/system/config', payload)
}
