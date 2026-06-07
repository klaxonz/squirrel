import { ref } from 'vue'
import { getSiteCatalog, getSites, saveSites } from '@/api'
import type { ApiResult } from '@/types/api'

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
  icon_url?: unknown
  [key: string]: unknown
}

type SiteOption = { value: SiteSlug; label: string }
type SitesResponse = Record<SiteSlug, SiteInfo>
type SiteListItem = SiteInfo & {
  name?: string
  site_name?: string
}
type SiteListResponse = {
  sites?: SiteListItem[]
}

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
  const { data, error: requestError } = (await getSites()) as ApiResult<SiteListResponse>
  if (requestError) {
    error.value = requestError
    loading.value = false
    return { data: cached.value, error: requestError }
  }

  const opts: SiteOption[] = []
  for (const site of data?.sites || []) {
    const slug = site.site_name || site.name
    if (slug && site.config_enabled !== false) {
      opts.push({ value: slug, label: site.label || slug })
    }
  }
  cached.value = opts
  loading.value = false
  return { data: cached.value, error: null }
}

export function useSites() {
  return { options: cached, loading, error, fetchSites }
}
const siteCatalog = ref<SitesResponse>({})
const siteCatalogLoading = ref(false)
const siteCatalogError = ref<unknown | null>(null)

type SiteCatalogPayloadItem = {
  [key: string]: unknown
}

type SiteCatalogPayload = Record<SiteSlug, SiteCatalogPayloadItem>

type SiteCatalogEditableItem = {
  label?: string
  aliases?: string[]
  enabled?: boolean
  icon_url?: unknown
  test_url?: unknown
  http?: unknown
  proxy?: unknown
  login?: unknown
  rate_limit?: unknown
  metadata?: unknown
}

export function useSiteCatalog() {
  const loadCatalog = async () => {
    siteCatalogLoading.value = true
    siteCatalogError.value = null
    const { data, error } = (await getSiteCatalog()) as ApiResult<SitesResponse>
    if (error) {
      siteCatalogError.value = error
    } else {
      siteCatalog.value = data || {}
    }
    siteCatalogLoading.value = false
  }

  const saveCatalog = async (updatedOverrides: SiteCatalogPayload) => {
    siteCatalogLoading.value = true
    siteCatalogError.value = null
    try {
      const result = (await saveSites({ sites: updatedOverrides })) as ApiResult<SitesResponse>
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
