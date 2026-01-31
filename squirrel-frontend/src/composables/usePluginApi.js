import { ApiError, get, post } from '../utils/request'

export function usePluginApi() {
  const getPlugins = async () => {
    return get('/api/plugins/')
  }

  const installPlugin = async (file) => {
    if (!file) {
      return { data: null, error: new ApiError('请选择插件包') }
    }

    const formData = new FormData()
    formData.append('file', file)

    return post('/api/plugins/install', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  }

  const enablePlugin = async (name) => {
    return post(`/api/plugins/${encodeURIComponent(name)}/enable`, null)
  }

  const disablePlugin = async (name) => {
    return post(`/api/plugins/${encodeURIComponent(name)}/disable`, null)
  }

  const uninstallPlugin = async (name) => {
    return post(`/api/plugins/${encodeURIComponent(name)}/uninstall`, null)
  }

  const reloadPlugins = async () => {
    return post('/api/plugins/reload', null)
  }

  const getSupportedSites = async () => {
    return get('/api/plugins/sites')
  }

  const testSiteConnectivity = async (siteName, timeout = 10) => {
    return get(`/api/plugins/sites/${encodeURIComponent(siteName)}/test-connectivity`, { timeout })
  }

  const testSiteLoginStatus = async (siteName) => {
    return get(`/api/plugins/sites/${encodeURIComponent(siteName)}/login-status`)
  }

  const testAllSitesConnectivity = async (timeout = 10) => {
    return get('/api/plugins/sites/test-connectivity/all', { timeout })
  }

  const importAllSiteCookies = async (file) => {
    if (!file) {
      return { data: null, error: new ApiError('请选择 Cookie 文件') }
    }

    const formData = new FormData()
    formData.append('file', file)

    return post('/api/plugins/sites/cookies/import-all', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  }

  const uploadSiteCookies = async (siteName, file, target = 'default') => {     
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

  const syncCookieCloudCookies = async (siteName = null) => {
    return post('/api/plugins/sites/cookies/cookiecloud/sync', null, {
      params: siteName ? { site_name: siteName } : {},
    })
  }

  return {
    getPlugins,
    installPlugin,
    enablePlugin,
    disablePlugin,
    uninstallPlugin,
    reloadPlugins,
    getSupportedSites,
    testSiteConnectivity,
    testSiteLoginStatus,
    testAllSitesConnectivity,
    importAllSiteCookies,
    uploadSiteCookies,
    syncCookieCloudCookies,
  };
}
