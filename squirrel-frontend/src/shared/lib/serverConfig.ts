import { getItem } from '@/shared/lib/storageKeys'

const readFromStorage = (): string => {
  if (typeof window === 'undefined') return ''
  return getItem('serverUrl') || ''
}

let cachedUrl = ''

export const getServerUrl = (): string => {
  return cachedUrl || readFromStorage()
}

export const updateServerUrlCache = (url: string): void => {
  cachedUrl = url
}
