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

/**
 * Turn backend-relative asset paths (e.g. `/api/sites/youtube/icon`) into
 * absolute URLs against the configured server. Absolute / data URLs pass through.
 */
export const resolveServerAssetUrl = (path: string | null | undefined): string | null => {
  const raw = String(path || '').trim()
  if (!raw) return null
  if (/^(https?:|data:|blob:)/i.test(raw)) return raw

  const base = getServerUrl().replace(/\/+$/, '')
  if (!base) {
    // Same-origin / vite proxy fallback when no explicit server is stored.
    return raw.startsWith('/') ? raw : `/${raw}`
  }

  if (raw.startsWith('/')) return `${base}${raw}`
  return `${base}/${raw}`
}
