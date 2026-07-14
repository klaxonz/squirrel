/**
 * Intentional site identity for dense UI (filters, chips) when raster icons
 * are missing or still loading. Colors are brand-adjacent, not random pastels.
 */

export type SiteBrand = {
  slug: string
  mono: string
  bg: string
  fg: string
}

const SITE_BRANDS: Record<string, Omit<SiteBrand, 'slug'>> = {
  bilibili: { mono: 'Bili', bg: '#FB7299', fg: '#FFFFFF' },
  youtube: { mono: 'YT', bg: '#FF0033', fg: '#FFFFFF' },
  javdb: { mono: 'JD', bg: '#2F6FED', fg: '#FFFFFF' },
  pornhub: { mono: 'PH', bg: '#FFA31A', fg: '#111111' },
  youporn: { mono: 'YP', bg: '#E53935', fg: '#FFFFFF' },
}

export function normalizeSiteSlug(site: string | null | undefined): string {
  return String(site || '').trim().toLowerCase()
}

export function getSiteBrand(site: string | null | undefined): SiteBrand | null {
  const slug = normalizeSiteSlug(site)
  if (!slug) return null
  const brand = SITE_BRANDS[slug]
  if (!brand) return null
  return { slug, ...brand }
}

/** Two-letter monogram for unknown sites. */
export function siteMonogram(label: string | null | undefined, site?: string | null): string {
  const brand = getSiteBrand(site)
  if (brand) return brand.mono

  const raw = String(label || site || '').trim()
  if (!raw) return '?'
  // Prefer first two Latin letters when present.
  const latin = raw.replace(/[^a-zA-Z0-9]/g, '')
  if (latin.length >= 2) return latin.slice(0, 2).toUpperCase()
  if (latin.length === 1) return latin.toUpperCase()
  const chars = Array.from(raw)
  return (chars[0] || '?').toUpperCase()
}
