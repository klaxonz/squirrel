import { get, post } from '@/utils/request'

export const getSystemConfig = async () => {
  return get('/api/system/config')
}

export const saveSystemConfig = async (payload = {}) => {
  return post('/api/system/config', payload)
}
