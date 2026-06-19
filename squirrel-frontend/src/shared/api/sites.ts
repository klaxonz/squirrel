import { get, put } from '@/shared/lib/request'
import type { SiteListResponse, SitesResponse } from '@/features/video/types/sites'

export const getSites = async () => {
  return get<SiteListResponse>('/api/sites')
}

export const getSiteCatalog = async () => {
  return get<SitesResponse>('/api/sites/catalog')
}

export const saveSites = async (payload: { sites: SitesResponse }) => {
  return put<SitesResponse>('/api/sites/catalog', payload)
}
