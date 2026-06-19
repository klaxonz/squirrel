// DTOs for /api/sites and /api/sites/catalog.

export type SiteSlug = string

export interface SiteInfo {
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

/** Site entry from GET /api/sites (catalog metadata + runtime-derived flags). */
export interface SiteListItem extends SiteInfo {
  name?: string
  site_name?: string
}

export interface SiteListResponse {
  sites?: SiteListItem[]
}

/** Catalog overrides map: slug -> SiteInfo, returned by GET /api/sites/catalog. */
export type SitesResponse = Record<SiteSlug, SiteInfo>

export interface SiteOption {
  value: SiteSlug
  label: string
}
