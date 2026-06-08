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

const ALL_SITE_NAMES = [
  'bilibili',
  'youtube',
  'pornhub',
  'youporn',
]

const SEARCH_TIMEOUT_MS = 30000
const JAVDB_SEARCH_TIMEOUT_MS = 90000
const ALL_SEARCH_WAIT_MS = 1800
const ALL_SEARCH_READY_GRACE_MS = 250
const ALL_SEARCH_MIN_READY_ITEMS = 12

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

const countCompletedItems = (siteResults) => {
  return siteResults.reduce((total, siteResult) => {
    return total + (Array.isArray(siteResult.items) ? siteResult.items.length : 0)
  }, 0)
}

const waitForAllSiteResults = async (searchTasks, waitMs, readyGraceMs, minReadyItems) => {
  const pending = new Set(searchTasks)
  const completed = []
  const errors = []
  const deadline = Date.now() + waitMs
  let readyDeadline = null

  while (pending.size > 0) {
    const activeDeadline = readyDeadline ? Math.min(deadline, readyDeadline) : deadline
    if (Date.now() >= activeDeadline) break
    const timeoutMs = activeDeadline - Date.now()
    const raceResult = await Promise.race([
      ...Array.from(pending).map((task) => task.promise),
      new Promise((resolve) => {
        setTimeout(() => resolve(null), timeoutMs)
      }),
    ])
    if (!raceResult) break

    pending.delete(raceResult.task)
    if (raceResult.status === 'fulfilled') {
      completed.push(raceResult.value)
      if (!readyDeadline && countCompletedItems(completed) >= minReadyItems) {
        readyDeadline = Date.now() + readyGraceMs
      }
    } else {
      errors.push(String(raceResult.reason?.message || raceResult.reason || 'Remote search failed'))
    }
  }

  return { completed, errors, pendingCount: pending.size }
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
  const siteNames = normalizedSite === 'all' ? ALL_SITE_NAMES : [normalizedSite]
  const unknownSite = siteNames.find((siteName) => !PROVIDERS[siteName])
  if (unknownSite) {
    throw new Error(`Remote search site is not supported: ${unknownSite}`)
  }

  const searchTasks = siteNames.map((siteName) => {
    const task = {}
    task.promise = searchProviderWithTimeout(siteName, {
      query: keyword,
      limit: resultLimit,
      page: resultPage,
      fetchImpl,
      buildCookieHeader,
      loadDocumentHtml,
    }, searchTimeoutMs, hasProviderTimeoutMs)
      .then((providerResult) => ({
        task,
        status: 'fulfilled',
        value: {
          site: siteName,
          items: Array.isArray(providerResult) ? providerResult : providerResult?.items,
          has_more: Array.isArray(providerResult) ? undefined : providerResult?.has_more,
        },
      }))
      .catch((reason) => ({
        task,
        status: 'rejected',
        reason,
      }))
    return task
  })

  const settled = normalizedSite === 'all'
    ? await waitForAllSiteResults(
      searchTasks,
      ALL_SEARCH_WAIT_MS,
      ALL_SEARCH_READY_GRACE_MS,
      Math.min(ALL_SEARCH_MIN_READY_ITEMS, resultLimit),
    )
    : await Promise.all(searchTasks.map((task) => task.promise)).then((results) => ({
        completed: results
          .filter((result) => result.status === 'fulfilled')
          .map((result) => result.value),
        errors: results
          .filter((result) => result.status === 'rejected')
          .map((result) => String(result.reason?.message || result.reason || 'Remote search failed')),
        pendingCount: 0,
      }))

  const siteResults = []
  const errors = [...settled.errors]
  const completedBySite = new Map(settled.completed.map((result) => [result.site, result]))
  for (const siteName of siteNames) {
    const completed = completedBySite.get(siteName)
    if (!completed) continue
    siteResults.push({
      site: completed.site,
      items: Array.isArray(completed.items) ? completed.items : [],
      has_more: completed.has_more,
    })
  }

  const hasPendingSites = settled.pendingCount > 0
  const dedupedItems = normalizedSite === 'all'
    ? interleaveSiteItems(siteResults, resultLimit)
    : uniqueByUrl(siteResults.flatMap((siteResult) => siteResult.items)).slice(0, resultLimit)
  const hasMore = siteResults.some((siteResult) => (
    siteResult.has_more === undefined ? siteResult.items.length >= resultLimit : siteResult.has_more === true
  ))

  return {
    items: dedupedItems,
    errors,
    sites: siteNames,
    pending_sites: hasPendingSites ? siteNames.filter((siteName) => !completedBySite.has(siteName)) : [],
    partial: hasPendingSites,
    page: resultPage,
    has_more: hasMore,
  }
}
