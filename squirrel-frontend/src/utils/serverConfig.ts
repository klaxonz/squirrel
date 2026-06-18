const CONFIG_KEY = 'squirrel_server_url'

const readFromStorage = (): string => {
  if (typeof window === 'undefined') return ''
  return localStorage.getItem(CONFIG_KEY) || ''
}

let cachedUrl = ''

export const getServerUrl = (): string => {
  return cachedUrl || readFromStorage()
}

export const updateServerUrlCache = (url: string): void => {
  cachedUrl = url
}
