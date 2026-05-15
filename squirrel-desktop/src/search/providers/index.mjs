import { searchBilibiliVideos } from './bilibili.mjs'
import { searchJavdbVideos } from './javdb.mjs'
import { searchPornhubVideos } from './pornhub.mjs'
import { clampLimit, normalizeQuery, uniqueByUrl } from './shared.mjs'
import { searchYouPornVideos } from './youporn.mjs'
import { searchYouTubeVideos } from './youtube.mjs'

const PROVIDERS = {
  bilibili: searchBilibiliVideos,
  javdb: searchJavdbVideos,
  pornhub: searchPornhubVideos,
  youporn: searchYouPornVideos,
  youtube: searchYouTubeVideos,
}

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

export const searchRemoteVideos = async ({ query, site = 'all', limit = 20, fetchImpl, buildCookieHeader }) => {
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
  const siteNames = normalizedSite === 'all' ? Object.keys(PROVIDERS) : [normalizedSite]
  const unknownSite = siteNames.find((siteName) => !PROVIDERS[siteName])
  if (unknownSite) {
    throw new Error(`Remote search site is not supported: ${unknownSite}`)
  }

  const settled = await Promise.allSettled(siteNames.map(async (siteName) => ({
    site: siteName,
    items: await PROVIDERS[siteName]({
      query: keyword,
      limit: resultLimit,
      fetchImpl,
      buildCookieHeader,
    }),
  })))

  const items = []
  const errors = []
  for (const result of settled) {
    if (result.status === 'fulfilled') {
      items.push(...result.value.items)
      continue
    }
    errors.push(String(result.reason?.message || result.reason || 'Remote search failed'))
  }

  return {
    items: uniqueByUrl(items).slice(0, resultLimit),
    errors,
    sites: siteNames,
  }
}
