import { ApiError, get, post } from '@/utils/request'

export const getPlugins = async () => {
  return get('/api/plugins/')
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
