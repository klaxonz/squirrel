import { ApiError, del, get, post } from '@/utils/request'

export interface PluginCapability {
  name: string
  description?: string
  request_schema?: Record<string, unknown>
  response_schema?: Record<string, unknown>
  timeout_ms?: number | null
  requires?: string[]
  metadata?: Record<string, unknown>
}

export interface PluginSite {
  site_name: string
  domains: string[]
  test_url?: string | null
  icon_url?: string | null
  features?: string[]
  metadata?: Record<string, unknown>
}

export interface PluginPermission {
  name: string
  description?: string
  required?: boolean
  scope?: string | null
  metadata?: Record<string, unknown>
}

export interface PluginHealth {
  healthy: boolean
  status?: string
  message?: string
  checked_at?: string | null
  details?: Record<string, unknown>
}

export interface PluginRuntimeInfo {
  plugin_id: string
  version: string
  state: string
  process_id?: number | null
  endpoint?: string | null
  started_at?: string | null
  drained_at?: string | null
  last_error?: string | null
  health?: PluginHealth | null
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

export interface PluginListItem {
  plugin_id: string
  display_name: string
  description?: string
  version: string
  enabled: boolean
  status: string
  capabilities: PluginCapability[]
  sites: PluginSite[]
  permissions: PluginPermission[]
  health?: PluginHealth | null
  active_runtime?: PluginRuntimeInfo | null
}

export const getPlugins = async () => {
  return get<PluginListItem[]>('/api/plugins/')
}

export const installPlugin = async (file: File | null | undefined) => {
  if (!file) {
    return { data: null, error: new ApiError('请选择插件包') }
  }

  const formData = new FormData()
  formData.append('file', file)

  return post('/api/plugins/install', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}

export const enablePlugin = async (name: string) => {
  return post(`/api/plugins/${encodeURIComponent(name)}/enable`, null)
}

export const disablePlugin = async (name: string) => {
  return post(`/api/plugins/${encodeURIComponent(name)}/disable`, null)
}

export const uninstallPlugin = async (name: string) => {
  return post(`/api/plugins/${encodeURIComponent(name)}/uninstall`, null)
}

export const reloadPlugins = async () => {
  return post('/api/plugins/reload', null)
}

export const getSupportedSites = async () => {
  return get('/api/plugins/sites')
}

export const testSiteConnectivity = async (siteName: string, timeout: number = 10) => {
  return get(`/api/plugins/sites/${encodeURIComponent(siteName)}/test-connectivity`, { timeout })
}

export const testSiteLoginStatus = async (siteName: string) => {
  return get(`/api/plugins/sites/${encodeURIComponent(siteName)}/login-status`)
}

export const testAllSitesConnectivity = async (timeout = 10) => {
  return get('/api/plugins/sites/test-connectivity/all', { timeout })
}

export const importAllSiteCookies = async (file: File | null | undefined) => {
  if (!file) {
    return { data: null, error: new ApiError('请选择 Cookie 文件') }
  }

  const formData = new FormData()
  formData.append('file', file)

  return post('/api/plugins/sites/cookies/import-all', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}

export const uploadSiteCookies = async (
  siteName: string,
  file: File | null | undefined,
  target: string = 'default'
) => {
  if (!file) {
    return { data: null, error: new ApiError('请选择 Cookie 文件') }
  }

  const formData = new FormData()
  formData.append('file', file)

  return post(`/api/plugins/sites/${encodeURIComponent(siteName)}/cookies`, formData, {
    params: { target },
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}

export const syncCookieCloudCookies = async (siteName: string | null = null) => {
  return post('/api/plugins/sites/cookies/cookiecloud/sync', null, {
    params: siteName ? { site_name: siteName } : {},
  })
}

export const setupYouTubeOAuth = async () => {
  return post<YouTubeOAuthState>('/api/plugins/sites/youtube/oauth/setup', null)
}

export const getYouTubeOAuthStatus = async () => {
  return get<YouTubeOAuthState>('/api/plugins/sites/youtube/oauth/status')
}

export const revokeYouTubeOAuth = async () => {
  return del<{ revoked: boolean }>('/api/plugins/sites/youtube/oauth')
}
