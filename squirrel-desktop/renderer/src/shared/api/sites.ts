import { del, get, post, put } from '@/shared/lib/request'
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

// --- Site cookies -----------------------------------------------------------

export const uploadSiteCookies = async (
  siteName: string,
  file: File | null | undefined,
  target: string = 'default'
) => {
  if (!file) {
    throw new Error('请选择登录凭据文件')
  }

  const formData = new FormData()
  formData.append('file', file)

  return post(`/api/site-cookies/${encodeURIComponent(siteName)}`, formData, {
    params: { target },
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}

export const syncCookieCloudCookies = async (siteName: string | null = null) => {
  return post('/api/site-cookies/cookiecloud/sync', null, {
    params: siteName ? { site_name: siteName } : {},
  })
}

// --- YouTube TV-code OAuth --------------------------------------------------

export interface YouTubeOAuthAccount {
  name?: string | null
  email?: string | null
  avatar?: string | null
}

export interface YouTubeOAuthState {
  status: string
  verification_url?: string | null
  user_code?: string | null
  account?: YouTubeOAuthAccount | null
  error?: string | null
}

export const setupYouTubeOAuth = async () => {
  return post<YouTubeOAuthState>('/api/sites/youtube/oauth/setup', null)
}

export const getYouTubeOAuthStatus = async () => {
  return get<YouTubeOAuthState>('/api/sites/youtube/oauth/status')
}

export const revokeYouTubeOAuth = async () => {
  return del<{ revoked: boolean }>('/api/sites/youtube/oauth')
}
