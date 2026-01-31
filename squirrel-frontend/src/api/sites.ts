import { get, put } from '@/utils/request'

export const getSites = async () => {
  return get('/api/sites')
}

export const saveSites = async (payload: Record<string, unknown>) => {
  return put('/api/sites', payload)
}
