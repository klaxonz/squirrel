import { ref } from 'vue'
import { getSites, saveSites } from '@/api'

type SiteSlug = string
type SiteInfo = {
  label?: string
  domains?: string[]
  aliases?: string[]
  enabled?: boolean
  http?: unknown
  proxy?: unknown
  login?: unknown
  rate_limit?: unknown
  metadata?: unknown
  test_url?: unknown
  [key: string]: unknown
}

type SiteOption = { value: SiteSlug | undefined; label: string }
type SitesResponse = Record<SiteSlug, SiteInfo>

type ApiResult<T> = { data?: T | null; error?: unknown | null }

const cached = ref<SiteOption[] | null>(null)
const loading = ref(false)
const error = ref<unknown | null>(null)

const resetCache = () => {
  cached.value = null
}

export async function fetchSites() {
  if (cached.value || loading.value) return { data: cached.value, error: error.value }
  loading.value = true
  error.value = null
  const { data, error: requestError } = (await getSites()) as ApiResult<SitesResponse>
  if (requestError) {
    error.value = requestError
    loading.value = false
    return { data: cached.value, error: requestError }
  }

  const items = data ? Object.entries(data) : []
  const opts: SiteOption[] = [{ value: undefined, label: '全部站点' }]
  for (const [slug, info] of items as Array<[SiteSlug, SiteInfo]>) {
    if (info && info.enabled !== false) {
      opts.push({ value: slug, label: info.label || slug })
    }
  }
  cached.value = opts
  loading.value = false
  return { data: cached.value, error: null }
}

export function useSites() {
  return { options: cached, loading, error, fetchSites, resetCache }
}

export function resetSitesCache() {
  resetCache()
}
const siteCatalog = ref<SitesResponse>({})
const siteCatalogLoading = ref(false)
const siteCatalogError = ref<unknown | null>(null)

type SiteCatalogPayloadItem = {
  slug: SiteSlug
  label: string
  domains: string[]
  aliases: string[]
  enabled: boolean
  http?: unknown
  proxy?: unknown
  login?: unknown
  rate_limit?: unknown
  metadata?: unknown
  test_url?: unknown
}

export function useSiteCatalog() {
  const loadCatalog = async () => {
    siteCatalogLoading.value = true
    siteCatalogError.value = null
    const { data, error } = (await getSites()) as ApiResult<SitesResponse>
    if (error) {
      siteCatalogError.value = error
    } else {
      siteCatalog.value = data || {}
    }
    siteCatalogLoading.value = false
  }

  const catalogObjectToPayload = (catalogObj: SitesResponse) => {
    return Object.entries(catalogObj).map(([slug, info]): SiteCatalogPayloadItem => {
      const payload: SiteCatalogPayloadItem = {
        slug,
        label: info?.label || slug,
        domains: info?.domains || [],
        aliases: info?.aliases || [],
        enabled: info?.enabled !== false,
      }
      if (info?.http) payload.http = info.http
      if (info?.proxy) payload.proxy = info.proxy
      if (info?.login) payload.login = info.login
      if (info?.rate_limit) payload.rate_limit = info.rate_limit
      if (info?.metadata) payload.metadata = info.metadata
      if (info?.test_url) payload.test_url = info.test_url
      return payload
    })
  }

  const saveCatalog = async (updatedCatalog: SitesResponse) => {
    siteCatalogLoading.value = true
    siteCatalogError.value = null
    try {
      const payload = catalogObjectToPayload(updatedCatalog)
      const result = (await saveSites({ sites: payload })) as ApiResult<SitesResponse>
      if (result.error) throw result.error

      siteCatalog.value = result.data || {}
      resetCache()
    } catch (e: unknown) {
      siteCatalogError.value = e
      throw e
    } finally {
      siteCatalogLoading.value = false
    }
  }

  return {
    catalog: siteCatalog,
    loading: siteCatalogLoading,
    error: siteCatalogError,
    loadCatalog,
    saveCatalog,
  }
}
