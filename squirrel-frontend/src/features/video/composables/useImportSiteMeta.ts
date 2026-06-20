import { ref, type Ref } from 'vue'
import { errorMessage } from '@/shared/lib/errorMessage'
import { getSupportedImportSites } from '@/shared/api'
import { useSiteCatalog } from '@/features/video/composables/useSites'

/**
 * Supported-import-site discovery + name/icon resolution.
 *
 * Loads the backend's list of importable sites (refreshing the site catalog so
 * icon/label lookups are fresh) and resolves a site key to a display name +
 * icon url, with a static fallback table for sites not in the catalog. The
 * shared `requestError` is injected so load failures surface on the same error
 * banner as the rest of the import flow.
 *
 * Extracted from ImportSubscriptionDialog.vue so the catalog-lookup +
 * fallback-table + load-policy live in one reusable place.
 */
const SITE_FALLBACK: Record<string, { name: string }> = {
  bilibili: { name: '哔哩哔哩' },
  youtube: { name: '油管' },
  pornhub: { name: '成人站点一' },
  youporn: { name: '成人站点二' },
  javdb: { name: '影片数据库' },
}

export interface UseImportSiteMetaOptions {
  /** Shared error ref; site-load failures write here. */
  requestError: Ref<string>
}

export interface UseImportSiteMetaReturn {
  supportedSites: Ref<string[]>
  /** The site catalog ref straight from useSiteCatalog (SitesResponse). */
  siteCatalog: ReturnType<typeof useSiteCatalog>['catalog']
  loadSupportedSites: () => Promise<void>
  getSiteName: (site: string) => string
  getSiteIconUrl: (site: string) => string | null
}

export function useImportSiteMeta(options: UseImportSiteMetaOptions): UseImportSiteMetaReturn {
  const { requestError } = options
  const { catalog: siteCatalog, loadCatalog } = useSiteCatalog()

  const supportedSites = ref<string[]>([])

  // Catalog entries use the catalog's own SitesResponse shape (icon_url is
  // unknown upstream); narrow per-field at the read sites below.
  const getSiteCatalogItem = (site: string): { label?: string; icon_url?: unknown } | null => {
    const key = (site?.toLowerCase?.() || site) as keyof typeof siteCatalog.value
    const entry = siteCatalog.value?.[key]
    return entry ?? null
  }

  const getSiteName = (site: string): string =>
    getSiteCatalogItem(site)?.label
    || SITE_FALLBACK[site]?.name
    || (site ? site.charAt(0).toUpperCase() + site.slice(1) : site)

  const getSiteIconUrl = (site: string): string | null => {
    const iconUrl = getSiteCatalogItem(site)?.icon_url
    return typeof iconUrl === 'string' && (iconUrl as string).trim() ? iconUrl : null
  }

  const loadSupportedSites = async () => {
    await loadCatalog()
    try {
      const data = await getSupportedImportSites()
      requestError.value = ''
      supportedSites.value = data
    } catch (err) {
      requestError.value = errorMessage(err, '加载可导入站点失败')
      supportedSites.value = []
    }
  }

  return {
    supportedSites,
    siteCatalog,
    loadSupportedSites,
    getSiteName,
    getSiteIconUrl,
  }
}
