import { loadFileCache, saveFileCache } from '../../../shared/file-cache.mjs'
import { CACHE_TTL_MS } from '../../../constants.mjs'

const caches = new Map()

const isExpired = (entry) => !entry || entry.expiresAt <= Date.now()

export const createPlaybackCache = (name) => {
  if (caches.has(name)) return caches.get(name)

  const cache = new Map()
  const fileCacheLoading = new Set()

  const getCachedPayload = async (cacheKey) => {
    const cached = cache.get(cacheKey)
    if (cached) {
      if (isExpired(cached)) {
        cache.delete(cacheKey)
      } else {
        return cached.value
      }
    }
    if (fileCacheLoading.has(cacheKey)) return null
    fileCacheLoading.add(cacheKey)
    try {
      const diskValue = await loadFileCache(cacheKey, CACHE_TTL_MS)
      if (diskValue) {
        cache.set(cacheKey, { value: diskValue, expiresAt: Date.now() + CACHE_TTL_MS })
        return diskValue
      }
    } finally {
      fileCacheLoading.delete(cacheKey)
    }
    return null
  }

  const setCachedPayload = (cacheKey, value) => {
    cache.set(cacheKey, {
      value,
      expiresAt: Date.now() + CACHE_TTL_MS,
    })
    saveFileCache(cacheKey, value, CACHE_TTL_MS).catch((err) => {
      console.debug(`[squirrel-desktop] ${name} cache save error`, err)
    })
  }

  const clearCache = () => cache.clear()

  const instance = { getCachedPayload, setCachedPayload, clearCache }
  caches.set(name, instance)
  return instance
}
