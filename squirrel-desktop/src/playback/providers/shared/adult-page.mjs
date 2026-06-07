import { loadFileCache, saveFileCache } from '../../file-cache.mjs'
import { CACHE_TTL_MS, desktopChromeUserAgent } from '../../../constants.mjs'
export { mergeCookieHeaders } from '../../../cookie-header.mjs'

const playbackCache = new Map()

export const DEFAULT_USER_AGENT = desktopChromeUserAgent

const isExpired = (entry) => {
  return !entry || entry.expiresAt <= Date.now()
}

const fileCacheLoading = new Set()

export const getCachedPayload = async (cacheKey) => {
  const cached = playbackCache.get(cacheKey)
  if (cached) {
    if (isExpired(cached)) {
      playbackCache.delete(cacheKey)
    } else {
      return cached.value
    }
  }
  if (fileCacheLoading.has(cacheKey)) return null
  fileCacheLoading.add(cacheKey)
  try {
    const diskValue = await loadFileCache(cacheKey, CACHE_TTL_MS)
    if (diskValue) {
      playbackCache.set(cacheKey, { value: diskValue, expiresAt: Date.now() + CACHE_TTL_MS })
      return diskValue
    }
  } finally {
    fileCacheLoading.delete(cacheKey)
  }
  return null
}

export const setCachedPayload = (cacheKey, value) => {
  playbackCache.set(cacheKey, {
    value,
    expiresAt: Date.now() + CACHE_TTL_MS,
  })
  saveFileCache(cacheKey, value, CACHE_TTL_MS).catch((err) => {
    console.debug('[squirrel-desktop] adult-page cache save error', err)
  })
}

export const clearAdultPlaybackCache = () => {
  playbackCache.clear()
}

export const normalizeTargetUrl = (targetUrl) => {
  const value = String(targetUrl || '').trim()
  if (!value) {
    return ''
  }

  try {
    return new URL(value).toString()
  } catch (err) {
    console.debug('[squirrel-desktop] normalizeTargetUrl error', err)
    return ''
  }
}

export const fetchPageHtml = async (
  targetUrl,
  {
    cookie = '',
    referer,
    origin,
    userAgent = DEFAULT_USER_AGENT,
    acceptLanguage = 'en-US,en;q=0.9',
    fetchImpl = globalThis.fetch,
    timeoutMs = 25000,
  } = {},
) => {
  const abortController = new AbortController()
  const timer = setTimeout(() => abortController.abort(), timeoutMs)

  try {
    const response = await fetchImpl(targetUrl, {
      headers: {
        'Accept-Language': acceptLanguage,
        'User-Agent': userAgent,
        Referer: referer,
        Origin: origin,
        ...(cookie ? { Cookie: cookie } : {}),
      },
      redirect: 'follow',
      signal: abortController.signal,
    })

    if (!response.ok) {
      throw new Error(`Adult page request failed with HTTP ${response.status}`)
    }

    return response.text()
  } finally {
    clearTimeout(timer)
  }
}

const readQuotedSegment = (source, startIndex, quote) => {
  let index = startIndex
  let escaped = false

  while (index < source.length) {
    const char = source[index]
    if (escaped) {
      escaped = false
      index += 1
      continue
    }

    if (char === '\\') {
      escaped = true
      index += 1
      continue
    }

    if (char === quote) {
      return index
    }

    index += 1
  }

  return -1
}

const readBalancedSegment = (source, startIndex, openChar, closeChar) => {
  if (source[startIndex] !== openChar) {
    return null
  }

  let depth = 0
  let index = startIndex

  while (index < source.length) {
    const char = source[index]

    if (char === '"' || char === '\'') {
      const stringEnd = readQuotedSegment(source, index + 1, char)
      if (stringEnd < 0) {
        return null
      }
      index = stringEnd + 1
      continue
    }

    if (char === openChar) {
      depth += 1
    } else if (char === closeChar) {
      depth -= 1
      if (depth === 0) {
        return source.slice(startIndex, index + 1)
      }
    }

    index += 1
  }

  return null
}

export const findObjectLiteralAfterPattern = (source, pattern) => {
  const match = pattern.exec(source)
  if (!match) {
    return null
  }

  const objectStart = source.indexOf('{', match.index + match[0].length)
  if (objectStart < 0) {
    return null
  }

  return readBalancedSegment(source, objectStart, '{', '}')
}

export const extractJsonArrayFromObjectLiteral = (objectLiteral, keyName) => {
  if (!objectLiteral) {
    return null
  }

  const keyPattern = new RegExp(`["']?${keyName}["']?\\s*:`, 'i')
  const match = keyPattern.exec(objectLiteral)
  if (!match) {
    return null
  }

  const arrayStart = objectLiteral.indexOf('[', match.index + match[0].length)
  if (arrayStart < 0) {
    return null
  }

  const arrayLiteral = readBalancedSegment(objectLiteral, arrayStart, '[', ']')
  if (!arrayLiteral) {
    return null
  }

  try {
    return JSON.parse(arrayLiteral)
  } catch (err) {
    console.debug('[squirrel-desktop] extractJsonArrayFromObjectLiteral error', err)
    return null
  }
}

export const safeInt = (value) => {
  const numeric = Number.parseInt(String(value ?? ''), 10)
  return Number.isFinite(numeric) ? numeric : 0
}

export const safeUrl = (value) => {
  const normalized = String(value || '').trim()
  return normalized || ''
}

export const pickBestDefinition = (definitions, format) => {
  const candidates = (Array.isArray(definitions) ? definitions : [])
    .filter((item) => String(item?.format || '').toLowerCase() === format)
    .filter((item) => safeUrl(item?.videoUrl))

  if (candidates.length === 0) {
    return null
  }

  return [...candidates].sort((left, right) => {
    const heightDelta = safeInt(right?.height || right?.quality) - safeInt(left?.height || left?.quality)
    if (heightDelta !== 0) {
      return heightDelta
    }

    const widthDelta = safeInt(right?.width) - safeInt(left?.width)
    if (widthDelta !== 0) {
      return widthDelta
    }

    return Number(Boolean(right?.defaultQuality)) - Number(Boolean(left?.defaultQuality))
  })[0]
}

export const buildHlsQualities = (definitions, idPrefix) => {
  const qualities = []
  const seen = new Set()

  for (const item of Array.isArray(definitions) ? definitions : []) {
    const format = String(item?.format || '').toLowerCase()
    if (format !== 'hls' || !safeUrl(item?.videoUrl)) {
      continue
    }

    const height = safeInt(item?.height || item?.quality) || null
    const width = safeInt(item?.width) || null
    const qualityId = `${idPrefix}:${width || 0}x${height || 0}`
    if (seen.has(qualityId)) {
      continue
    }
    seen.add(qualityId)

    qualities.push({
      id: qualityId,
      value: qualityId,
      label: height ? `${height}p` : qualityId,
      height,
      bandwidth: null,
      codec: null,
    })
  }

  qualities.sort((left, right) => safeInt(right.height) - safeInt(left.height))
  return qualities
}
