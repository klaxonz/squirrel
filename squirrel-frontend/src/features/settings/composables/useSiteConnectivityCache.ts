import { ref, type Ref } from 'vue'
import { Logger } from '@/shared/lib/logger'
import { mergeLoginStatusResult, type SiteLoginStatus } from '@/shared/lib/site-runtime-login-status'

/**
 * Connectivity + login-status result storage with localStorage persistence.
 *
 * Owns the four result buckets the SiteRuntimeManager view renders against
 * (connectivity results, per-site login status, per-site "testing" flags, and
 * the last-tested timestamp), plus their cache round-trip and the login-status
 * upsert merge. Extracted verbatim from SiteRuntimeManager.vue so the
 * persistence policy + the merge seam live in one place rather than interleaved
 * with the desktop-login and runtime-action handlers.
 */
const CACHE_KEY_CONNECTIVITY = 'squirrel_connectivity_results'
const CACHE_KEY_LOGIN_STATUS = 'squirrel_login_status_results'
const CACHE_KEY_LAST_TESTED = 'squirrel_last_tested_at'

/** One entry in the backend's all-sites connectivity batch result. */
interface ConnectivityBatch {
  results: ConnectivityResult[]
  summary: ConnectivitySummary
}

interface ConnectivityResult {
  site_name: string
  accessible?: boolean
  testing?: boolean
  [key: string]: unknown
}

interface ConnectivitySummary {
  total: number
  accessible: number
  failed: number
  success_rate: number
}

export interface UseSiteConnectivityCacheReturn {
  connectivityResults: Ref<ConnectivityBatch[]>
  loginStatusResults: Ref<Record<string, SiteLoginStatus | null | undefined>>
  loginStatusTesting: Ref<Record<string, boolean>>
  lastTestedAt: Ref<string | null>
  clearLoginStatusCache: () => void
  saveResultsToCache: () => void
  loadResultsFromCache: () => void
  upsertLoginStatus: (siteName: string, payload: SiteLoginStatus | null | undefined) => void
}

export function useSiteConnectivityCache(): UseSiteConnectivityCacheReturn {
  const connectivityResults = ref<ConnectivityBatch[]>([])
  const loginStatusResults = ref<Record<string, SiteLoginStatus | null | undefined>>({})
  const loginStatusTesting = ref<Record<string, boolean>>({})
  const lastTestedAt = ref<string | null>(null)

  const clearLoginStatusCache = () => {
    loginStatusResults.value = {}
    try {
      localStorage.removeItem(CACHE_KEY_LOGIN_STATUS)
    } catch (error) {
      Logger.warn('Failed to clear login status cache', error)
    }
  }

  const saveResultsToCache = () => {
    try {
      if (connectivityResults.value.length > 0) {
        localStorage.setItem(CACHE_KEY_CONNECTIVITY, JSON.stringify(connectivityResults.value))
      }
      if (Object.keys(loginStatusResults.value).length > 0) {
        localStorage.setItem(CACHE_KEY_LOGIN_STATUS, JSON.stringify(loginStatusResults.value))
      }
      const now = new Date().toISOString()
      lastTestedAt.value = now
      localStorage.setItem(CACHE_KEY_LAST_TESTED, now)
    } catch (error) {
      Logger.warn('Failed to save connectivity cache', error)
    }
  }

  const loadResultsFromCache = () => {
    try {
      const cachedConnectivity = localStorage.getItem(CACHE_KEY_CONNECTIVITY)
      const cachedLoginStatus = localStorage.getItem(CACHE_KEY_LOGIN_STATUS)
      const cachedLastTested = localStorage.getItem(CACHE_KEY_LAST_TESTED)

      if (cachedConnectivity) {
        connectivityResults.value = JSON.parse(cachedConnectivity)
      }
      if (cachedLoginStatus) {
        loginStatusResults.value = JSON.parse(cachedLoginStatus)
      }
      if (cachedLastTested) {
        lastTestedAt.value = cachedLastTested
      }
    } catch (error) {
      Logger.warn('Failed to load connectivity cache', error)
    }
  }

  // Merge a fresh login-status payload into the per-site map. The merge helper
  // keeps prior fields (e.g. oauth_status) that the new payload may omit.
  const upsertLoginStatus = (siteName: string, payload: SiteLoginStatus | null | undefined) => {
    loginStatusResults.value = {
      ...loginStatusResults.value,
      [siteName]: mergeLoginStatusResult(loginStatusResults.value?.[siteName], payload),
    }
  }

  return {
    connectivityResults,
    loginStatusResults,
    loginStatusTesting,
    lastTestedAt,
    clearLoginStatusCache,
    saveResultsToCache,
    loadResultsFromCache,
    upsertLoginStatus,
  }
}

