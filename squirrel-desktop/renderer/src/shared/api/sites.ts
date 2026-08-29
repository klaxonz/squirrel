import { ApiError, del, get, post, put } from '@/shared/lib/request'
import type { SiteListResponse, SitesResponse } from '@/features/video/types/sites'
import type { SiteLoginStatus } from '@/shared/lib/site-runtime-login-status'

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

export interface SiteConnectivityResult {
  site_name: string
  domains?: string[]
  test_url?: string | null
  accessible: boolean
  status?: string
  status_code?: number | null
  response_time?: number | null
  dns_resolved?: boolean
  ip_address?: string | null
  error_message?: string | null
}

export interface SiteConnectivitySummary {
  total: number
  accessible: number
  failed: number
  success_rate: number
  avg_response_time?: number | null
}

export interface SiteConnectivityAllResponse {
  results: SiteConnectivityResult[]
  summary: SiteConnectivitySummary
}

// --- Site runtime probes (connectivity / login status / bulk cookie import) --

export const getSupportedSites = async () => {
  return get<{ sites?: Array<Record<string, unknown>> }>('/api/sites')
}

export const importAllSiteCookies = async (file: File | null | undefined) => {
  if (!file) {
    throw new ApiError('请选择登录凭据文件')
  }

  const formData = new FormData()
  formData.append('file', file)

  return post<{ file_name?: string; total_lines?: number; matched_lines?: number; sites?: Record<string, { cookies: number }> }>(
    '/api/site-cookies/import-all',
    formData,
    { headers: { 'Content-Type': 'multipart/form-data' } },
  )
}

export const testAllSitesConnectivity = async (timeout = 10) => {
  return get<SiteConnectivityAllResponse>('/api/sites/test-connectivity/all', { timeout })
}

export const testSiteConnectivity = async (siteName: string, timeout = 10) => {
  return get<SiteConnectivityResult>(`/api/sites/${encodeURIComponent(siteName)}/test-connectivity`, { timeout })
}

export const testSiteLoginStatus = async (siteName: string) => {
  return get<SiteLoginStatus>(`/api/sites/${encodeURIComponent(siteName)}/login-status`)
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
