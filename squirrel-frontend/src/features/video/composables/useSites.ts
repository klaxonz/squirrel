import { ref } from 'vue'
import { getSiteCatalog, getSites, saveSites } from '@/shared/api'
import type { SiteOption, SitesResponse } from '@/features/video/types/sites'

type SiteSlug = string
type SiteCatalogPayloadItem = {
  [key: string]: unknown
}

type SiteCatalogPayload = Record<SiteSlug, SiteCatalogPayloadItem>

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
  const { data, error: requestError } = await getSites()
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

export function useSiteCatalog() {
  const loadCatalog = async () => {
    siteCatalogLoading.value = true
    siteCatalogError.value = null
    const { data, error } = await getSiteCatalog()
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
      const response = await saveSites({ sites: updatedOverrides })
      if (response.error) throw response.error

      siteCatalog.value = response.data || {}
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
