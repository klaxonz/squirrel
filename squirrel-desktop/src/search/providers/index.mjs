import { searchBilibiliVideos } from './bilibili.mjs'
import { searchJavdbVideos } from './javdb.mjs'
import { searchPornhubVideos } from './pornhub.mjs'
import { clampLimit, clampPage, normalizeQuery, uniqueByUrl } from './shared.mjs'
import { searchYouPornVideos } from './youporn.mjs'
import { searchYouTubeVideos } from './youtube.mjs'

const PROVIDERS = {
  bilibili: searchBilibiliVideos,
  javdb: searchJavdbVideos,
  pornhub: searchPornhubVideos,
  youporn: searchYouPornVideos,
  youtube: searchYouTubeVideos,
}

const SEARCH_TIMEOUT_MS = 30000
const JAVDB_SEARCH_TIMEOUT_MS = 90000

const SITE_ALIASES = {
  all: 'all',
  bili: 'bilibili',
  b23: 'bilibili',
  'b23.tv': 'bilibili',
  'bilibili.com': 'bilibili',
  'javdb.com': 'javdb',
  ph: 'pornhub',
  'pornhub.com': 'pornhub',
  'youtube.com': 'youtube',
  'youtu.be': 'youtube',
  'youporn.com': 'youporn',
}

const normalizeSite = (site) => {
  const rawValue = String(site || 'all').trim().toLowerCase()
  if (!rawValue) return 'all'
  const normalized = rawValue.replace(/^www\./, '')
  return SITE_ALIASES[normalized] || normalized
}

export const listRemoteSearchSites = () => Object.keys(PROVIDERS)

const searchProviderWithTimeout = async (siteName, options, timeoutMs, timeoutOverridden) => {
  let timer
  const siteTimeoutMs = siteName === 'javdb' && !timeoutOverridden ? JAVDB_SEARCH_TIMEOUT_MS : timeoutMs
  try {
    return await Promise.race([
      PROVIDERS[siteName](options),
      new Promise((_, reject) => {
        timer = setTimeout(() => reject(new Error(`${siteName} search timed out`)), siteTimeoutMs)
      }),
    ])
  } finally {
    clearTimeout(timer)
  }
}

const interleaveSiteItems = (siteResults, limit) => {
  const output = []
  const seenUrls = new Set()
  let index = 0

  while (output.length < limit) {
    let appended = false
    for (const siteResult of siteResults) {
      const item = siteResult.items[index]
      if (!item) continue
      const url = String(item?.url || '').trim()
      if (!url || seenUrls.has(url)) continue
      seenUrls.add(url)
      output.push(item)
      appended = true
      if (output.length >= limit) break
    }

    if (!appended) break
    index++
  }

  return output
}

export const searchRemoteVideos = async ({
  query,
  site = 'all',
  limit = 20,
  page = 1,
  fetchImpl,
  buildCookieHeader,
  loadDocumentHtml,
  providerTimeoutMs,
}) => {
  const keyword = normalizeQuery(query)
  if (!keyword) {
    return { items: [], errors: [], sites: [] }
  }

  if (typeof fetchImpl !== 'function') {
    throw new Error('Search fetch implementation is required')
  }
  if (typeof buildCookieHeader !== 'function') {
    throw new Error('Search cookie resolver is required')
  }

  const normalizedSite = normalizeSite(site)
  const resultLimit = clampLimit(limit)
  const resultPage = clampPage(page)
  const parsedProviderTimeoutMs = Number(providerTimeoutMs)
  const hasProviderTimeoutMs = Number.isFinite(parsedProviderTimeoutMs) && parsedProviderTimeoutMs > 0
  const searchTimeoutMs = hasProviderTimeoutMs ? parsedProviderTimeoutMs : SEARCH_TIMEOUT_MS
  const siteNames = normalizedSite === 'all' ? Object.keys(PROVIDERS) : [normalizedSite]
  const unknownSite = siteNames.find((siteName) => !PROVIDERS[siteName])
  if (unknownSite) {
    throw new Error(`Remote search site is not supported: ${unknownSite}`)
  }

  const settled = await Promise.allSettled(siteNames.map(async (siteName) => ({
    site: siteName,
    items: await searchProviderWithTimeout(siteName, {
      query: keyword,
      limit: resultLimit,
      page: resultPage,
      fetchImpl,
      buildCookieHeader,
      loadDocumentHtml,
    }, searchTimeoutMs, hasProviderTimeoutMs),
  })))

  const siteResults = []
  const errors = []
  for (const result of settled) {
    if (result.status === 'fulfilled') {
      siteResults.push({
        site: result.value.site,
        items: Array.isArray(result.value.items) ? result.value.items : [],
      })
      continue
    }
    errors.push(String(result.reason?.message || result.reason || 'Remote search failed'))
  }

  const dedupedItems = normalizedSite === 'all'
    ? interleaveSiteItems(siteResults, resultLimit)
    : uniqueByUrl(siteResults.flatMap((siteResult) => siteResult.items)).slice(0, resultLimit)
  const hasMore = siteResults.some((siteResult) => siteResult.items.length >= resultLimit)

  return {
    items: dedupedItems,
    errors,
    sites: siteNames,
    page: resultPage,
    has_more: hasMore,
  }
}
