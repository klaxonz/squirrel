import { get, put } from '@/utils/request'

export const getSites = async () => {
  return get('/api/sites')
}

export const getSiteCatalog = async () => {
  return get('/api/sites/catalog')
}

export const saveSites = async (payload: Record<string, unknown>) => {
  return put('/api/sites/catalog', payload)
}
