import { ApiError, del, get, post } from '@/utils/request'

export interface SiteRuntimeCapability {
  name: string
  description?: string
  request_schema?: Record<string, unknown>
  response_schema?: Record<string, unknown>
  timeout_ms?: number | null
  requires?: string[]
  metadata?: Record<string, unknown>
}

export interface SiteRuntimeSite {
  site_name: string
  domains: string[]
  test_url?: string | null
  icon_url?: string | null
  features?: string[]
  metadata?: Record<string, unknown>
}

export interface SiteRuntimePermission {
  name: string
  description?: string
  required?: boolean
  scope?: string | null
  metadata?: Record<string, unknown>
}

export interface SiteRuntimeHealth {
  healthy: boolean
  status?: string
  message?: string
  checked_at?: string | null
  details?: Record<string, unknown>
}

export interface SiteRuntimeInfo {
  runtime_id: string
  version: string
  state: string
  process_id?: number | null
  endpoint?: string | null
  started_at?: string | null
  drained_at?: string | null
  last_error?: string | null
  health?: SiteRuntimeHealth | null
}

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

export interface SiteRuntimeListItem {
  runtime_id: string
  display_name: string
  description?: string
  version: string
  enabled: boolean
  status: string
  capabilities: SiteRuntimeCapability[]
  sites: SiteRuntimeSite[]
  permissions: SiteRuntimePermission[]
  health?: SiteRuntimeHealth | null
  active_runtime?: SiteRuntimeInfo | null
}

export interface SiteRuntimeDiscoveryError {
  metadata_path: string
  reason: string
}

export interface SiteRuntimeListResponse {
  items: SiteRuntimeListItem[]
  discovery_errors: SiteRuntimeDiscoveryError[]
}

export const getSiteRuntimes = async () => {
  return get<SiteRuntimeListResponse>('/api/site-runtimes/')
}

export const enableSiteRuntime = async (name: string) => {
  return post(`/api/site-runtimes/${encodeURIComponent(name)}/enable`, null)
}

export const disableSiteRuntime = async (name: string) => {
  return post(`/api/site-runtimes/${encodeURIComponent(name)}/disable`, null)
}

export const reloadSiteRuntimes = async () => {
  return post('/api/site-runtimes/reload', null)
}

export const getSupportedSites = async () => {
  return get<{ sites?: Array<Record<string, unknown>> }>('/api/sites')
}

export const testSiteConnectivity = async (siteName: string, timeout: number = 10) => {
  return get(`/api/sites/${encodeURIComponent(siteName)}/test-connectivity`, { timeout })
}

export const testSiteLoginStatus = async (siteName: string) => {
  return get(`/api/sites/${encodeURIComponent(siteName)}/login-status`)
}

export const testAllSitesConnectivity = async (timeout = 10) => {
  return get('/api/sites/test-connectivity/all', { timeout })
}

export const importAllSiteCookies = async (file: File | null | undefined) => {
  if (!file) {
    return { data: null, error: new ApiError('请选择登录凭据文件') }
  }

  const formData = new FormData()
  formData.append('file', file)

  return post('/api/site-cookies/import-all', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}

export const uploadSiteCookies = async (
  siteName: string,
  file: File | null | undefined,
  target: string = 'default'
) => {
  if (!file) {
    return { data: null, error: new ApiError('请选择登录凭据文件') }
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

export const setupYouTubeOAuth = async () => {
  return post<YouTubeOAuthState>('/api/sites/youtube/oauth/setup', null)
}

export const getYouTubeOAuthStatus = async () => {
  return get<YouTubeOAuthState>('/api/sites/youtube/oauth/status')
}

export const revokeYouTubeOAuth = async () => {
  return del<{ revoked: boolean }>('/api/sites/youtube/oauth')
}


