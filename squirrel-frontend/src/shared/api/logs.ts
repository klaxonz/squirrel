import { get } from '@/shared/lib/request'

export const getLogFiles = async () => {
  return get('/api/logs/files')
}

export const queryLogs = async (params = {}) => {
  return get('/api/logs/query', params)
}
