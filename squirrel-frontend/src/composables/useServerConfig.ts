import { ref } from 'vue'

const CONFIG_KEY = 'squirrel_server_url'
const CONFIG_VERSION_KEY = 'squirrel_server_url_version'
const RECENT_SERVER_URLS_KEY = 'squirrel_recent_server_urls'
const MAX_RECENT_SERVER_URLS = 5

const serverUrl = ref<string>('')
const hasServerConfig = ref(false)
const recentServerUrls = ref<string[]>([])

let initPromise: Promise<string> | null = null
let hasBoundDesktopListener = false

const normalizeServerUrl = (value: unknown): string => {
  const normalized = String(value || '').trim()
  if (!normalized) return ''

  try {
    const parsed = new URL(normalized)
    if (!['http:', 'https:'].includes(parsed.protocol)) {
      return ''
    }
    return parsed.origin
  } catch {
    return ''
  }
}

const readFromStorage = (): string => {
  if (typeof window === 'undefined') return ''
  return normalizeServerUrl(localStorage.getItem(CONFIG_KEY))
}

const readRecentServerUrlsFromStorage = (): string[] => {
  if (typeof window === 'undefined') return []

  try {
    const rawValue = localStorage.getItem(RECENT_SERVER_URLS_KEY)
    if (!rawValue) return []

    const parsed = JSON.parse(rawValue)
    if (!Array.isArray(parsed)) return []

    return parsed
      .map((value) => normalizeServerUrl(value))
      .filter((value, index, values) => !!value && values.indexOf(value) === index)
      .slice(0, MAX_RECENT_SERVER_URLS)
  } catch {
    return []
  }
}

const writeToStorage = (url: string) => {
  if (typeof window === 'undefined') return

  if (url) {
    localStorage.setItem(CONFIG_KEY, url)
    localStorage.setItem(CONFIG_VERSION_KEY, '1')
    return
  }

  localStorage.removeItem(CONFIG_KEY)
  localStorage.removeItem(CONFIG_VERSION_KEY)
}

const writeRecentServerUrlsToStorage = (urls: string[]) => {
  if (typeof window === 'undefined') return

  if (!urls.length) {
    localStorage.removeItem(RECENT_SERVER_URLS_KEY)
    return
  }

  localStorage.setItem(RECENT_SERVER_URLS_KEY, JSON.stringify(urls))
}

const syncRecentServerUrlsState = (urls: string[]) => {
  recentServerUrls.value = urls
  writeRecentServerUrlsToStorage(urls)
}

const rememberRecentServerUrl = (url: string) => {
  if (!url) return

  const nextUrls = [url, ...recentServerUrls.value.filter((item) => item !== url)].slice(0, MAX_RECENT_SERVER_URLS)
  syncRecentServerUrlsState(nextUrls)
}

const syncServerUrlState = (url: string) => {
  serverUrl.value = url
  hasServerConfig.value = !!url
  initPromise = Promise.resolve(url)
  writeToStorage(url)
  if (url) {
    rememberRecentServerUrl(url)
  }
}

const readFromDesktopBridge = async (): Promise<string> => {
  if (typeof window === 'undefined') return ''

  const bridge = window.desktopApp
  if (bridge?.isDesktop !== true || typeof bridge.getServerUrl !== 'function') {
    return ''
  }

  try {
    return normalizeServerUrl(await bridge.getServerUrl())
  } catch {
    return ''
  }
}

const bindDesktopServerUrlListener = () => {
  if (typeof window === 'undefined' || hasBoundDesktopListener) return

  const bridge = window.desktopApp
  if (bridge?.isDesktop !== true || typeof bridge.onServerUrlChange !== 'function') {
    return
  }

  bridge.onServerUrlChange((value) => {
    syncServerUrlState(normalizeServerUrl(value))
  })
  hasBoundDesktopListener = true
}

export const initServerConfig = async (): Promise<string> => {
  bindDesktopServerUrlListener()

  if (initPromise) {
    return initPromise
  }

  initPromise = (async () => {
    const bridgeUrl = await readFromDesktopBridge()
    const storageUrl = readFromStorage()
    const resolvedUrl = bridgeUrl || storageUrl
    syncRecentServerUrlsState(readRecentServerUrlsFromStorage())
    syncServerUrlState(resolvedUrl)
    return resolvedUrl
  })()

  return initPromise
}

export const reloadFromBridge = async (): Promise<string> => {
  initPromise = null
  return initServerConfig()
}

export const getServerUrl = (): string => {
  return serverUrl.value || readFromStorage()
}

export const setServerUrl = async (url: string): Promise<boolean> => {
  const normalizedUrl = normalizeServerUrl(url)
  if (!normalizedUrl) return false

  if (typeof window !== 'undefined') {
    const bridge = window.desktopApp
    if (bridge?.isDesktop === true && typeof bridge.setServerUrl === 'function') {
      try {
        const persistedUrl = normalizeServerUrl(await bridge.setServerUrl(normalizedUrl))
        if (!persistedUrl) {
          return false
        }
        syncServerUrlState(persistedUrl)
        return true
      } catch {
        return false
      }
    }
  }

  syncServerUrlState(normalizedUrl)
  return true
}

export const clearServerConfig = async (): Promise<void> => {
  if (typeof window !== 'undefined') {
    const bridge = window.desktopApp
    if (bridge?.isDesktop === true && typeof bridge.clearServerUrl === 'function') {
      try {
        await bridge.clearServerUrl()
      } catch {
        // Ignore bridge cleanup failures and still clear local state.
      }
    }
  }

  syncServerUrlState('')
}

export const clearRecentServerUrls = () => {
  syncRecentServerUrlsState([])
}

export const testServerConnection = async (url: string): Promise<{ ok: boolean; message: string }> => {
  const baseUrl = normalizeServerUrl(url)
  if (!baseUrl) {
    return { ok: false, message: '无效的地址格式' }
  }

  try {
    const controller = new AbortController()
    const timeoutId = setTimeout(() => controller.abort(), 8000)

    const response = await fetch(`${baseUrl}/health/live`, {
      method: 'GET',
      signal: controller.signal,
    })

    clearTimeout(timeoutId)

    if (response.ok) {
      return { ok: true, message: '连接成功' }
    }

    return { ok: false, message: `服务器返回 ${response.status}` }
  } catch (error) {
    if (error instanceof DOMException && error.name === 'AbortError') {
      return { ok: false, message: '连接超时，请检查地址是否正确' }
    }

    return { ok: false, message: '无法连接到服务器' }
  }
}

export const useServerConfig = () => {
  return {
    serverUrl,
    hasServerConfig,
    recentServerUrls,
    initServerConfig,
    reloadFromBridge,
    getServerUrl,
    setServerUrl,
    clearServerConfig,
    clearRecentServerUrls,
    testServerConnection,
  }
}
