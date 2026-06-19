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
  if (cached.value || loading.value) return { data: cached.value, error: null }
  loading.value = true
  error.value = null
  try {
    const data = await getSites()
    const opts: SiteOption[] = []
    for (const site of data?.sites || []) {
      const slug = site.site_name || site.name
      if (slug && site.config_enabled !== false) {
        opts.push({ value: slug, label: site.label || slug })
      }
    }
    cached.value = opts
    return { data: cached.value, error: null }
  } catch (requestError) {
    error.value = requestError
    return { data: cached.value, error: requestError }
  } finally {
    loading.value = false
  }
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
    try {
      const data = await getSiteCatalog()
      siteCatalog.value = data || {}
    } catch (e: unknown) {
      siteCatalogError.value = e
    } finally {
      siteCatalogLoading.value = false
    }
  }

  const saveCatalog = async (updatedOverrides: SiteCatalogPayload) => {
    siteCatalogLoading.value = true
    siteCatalogError.value = null
    try {
      const data = await saveSites({ sites: updatedOverrides })
      siteCatalog.value = data || {}
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
