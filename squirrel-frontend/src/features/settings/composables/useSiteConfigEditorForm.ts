import { computed, ref, watch, type ComputedRef, type Ref } from 'vue'
import {
  headersToText,
  parseHeadersText,
  parseListInput,
  toNumberOrUndefined,
} from '@/features/settings/lib/siteConfigFormConverters'

/**
 * Site-config editor form state machine.
 *
 * Owns the form model (text-friendly representations of the backend's
 * structured site config), the local validation error, and the hydrate /
 * reset / validate / serialize flows. `handleSave` validates (slug required),
 * serialises the form into the backend's nested payload shape (metadata /
 * http / rate_limit / proxy / login), and emits a save event the host forwards
 * to its API call.
 *
 * Hydration re-runs whenever the dialog becomes visible or the underlying
 * site/catalog props change (deep) — so editing a different site or a catalog
 * refresh re-populates the form without stale fields.
 *
 * Extracted from SiteConfigEditorDialog.vue so the form's field set, the
 * hydrate mapping (site + catalog -> form), and the serialize mapping (form ->
 * nested payload) live in one auditable place rather than a 287-line script.
 */

/** Text-friendly form model — backend structured fields flattened for editing. */
export interface SiteEditorForm {
  slug: string
  siteName: string
  label: string
  domainsText: string
  aliasesText: string
  enabled: boolean
  testUrl: string
  iconUrl: string
  httpHeadersText: string
  rateLimitEnabled: boolean
  rateLimitMin: string
  rateLimitMax: string
  proxyConnectTimeout: string
  proxyReadTimeout: string
  proxyWriteTimeout: string
  proxyPoolTimeout: string
  proxyKeepaliveExpiry: string
  proxyMaxConnections: string
  proxyMaxKeepaliveConnections: string
  proxyChunkSize: string
  proxyMaxRetries: string
  proxyEnableHttp2: boolean
  proxyFollowRedirects: boolean
  loginCheckUrl: string
  loginHeadersText: string
  loginTimeout: string
  metadataNsfw: boolean
  metadataRequiresCookies: boolean
  metadataRequiresLogin: boolean
  metadataOfflineThumbnailsDownload: boolean
  metadataOfflineThumbnailsDisplay: boolean
}

const createEmptyForm = (): SiteEditorForm => ({
  slug: '',
  siteName: '',
  label: '',
  domainsText: '',
  aliasesText: '',
  enabled: true,
  testUrl: '',
  iconUrl: '',
  httpHeadersText: '',
  rateLimitEnabled: true,
  rateLimitMin: '',
  rateLimitMax: '',
  proxyConnectTimeout: '',
  proxyReadTimeout: '',
  proxyWriteTimeout: '',
  proxyPoolTimeout: '',
  proxyKeepaliveExpiry: '',
  proxyMaxConnections: '',
  proxyMaxKeepaliveConnections: '',
  proxyChunkSize: '',
  proxyMaxRetries: '',
  proxyEnableHttp2: true,
  proxyFollowRedirects: true,
  loginCheckUrl: '',
  loginHeadersText: '',
  loginTimeout: '',
  metadataNsfw: false,
  metadataRequiresCookies: false,
  metadataRequiresLogin: false,
  metadataOfflineThumbnailsDownload: false,
  metadataOfflineThumbnailsDisplay: false,
})

/**
 * Backend site/config payloads are genuinely schema-less (the catalog is a
 * heterogeneous map of per-site config blobs with no shared type). This loose
 * type is the single, audited escape hatch for that boundary — field reads use
 * optional chaining + `||` / `??` fallbacks so `any` never propagates past the
 * hydrated SiteEditorForm, which IS strictly typed.
 */
// eslint-disable-next-line @typescript-eslint/no-explicit-any
type LooseRecord = Record<string, any>

const asString = (value: unknown): string => (typeof value === 'string' ? value : '')

const buildFormFromSite = (site: LooseRecord | null | undefined, catalog: LooseRecord): SiteEditorForm => {
  const siteName = asString(site?.site_name || site?.name || site?.label || site?.slug)
  const slug = asString(site?.slug) || siteName.toLowerCase()
  const catalogInfo: LooseRecord = catalog?.[slug] || {}
  const rateLimit: LooseRecord = catalogInfo?.rate_limit || {}
  const proxy: LooseRecord = catalogInfo?.proxy || {}
  const loginConfig: LooseRecord = catalogInfo?.login || {}
  const metadata: LooseRecord = catalogInfo?.metadata || {}

  return {
    slug,
    siteName,
    label: asString(catalogInfo?.label || site?.label) || siteName || slug,
    domainsText: (catalogInfo?.domains?.length ? catalogInfo.domains : (site?.domains || [])).join('\n'),
    aliasesText: (catalogInfo?.aliases || []).join('\n'),
    enabled: catalogInfo?.enabled !== false,
    testUrl: catalogInfo?.test_url || site?.test_url || '',
    iconUrl: catalogInfo?.icon_url || site?.icon_url || '',
    httpHeadersText: headersToText(catalogInfo?.http?.headers || {}),
    rateLimitEnabled: rateLimit?.enabled !== false,
    rateLimitMin: rateLimit?.min_interval ?? '',
    rateLimitMax: rateLimit?.max_interval ?? '',
    proxyConnectTimeout: proxy?.connect_timeout ?? '',
    proxyReadTimeout: proxy?.read_timeout ?? '',
    proxyWriteTimeout: proxy?.write_timeout ?? '',
    proxyPoolTimeout: proxy?.pool_timeout ?? '',
    proxyKeepaliveExpiry: proxy?.keepalive_expiry ?? '',
    proxyMaxConnections: proxy?.max_connections ?? '',
    proxyMaxKeepaliveConnections: proxy?.max_keepalive_connections ?? '',
    proxyChunkSize: proxy?.chunk_size ?? '',
    proxyMaxRetries: proxy?.max_retries ?? '',
    proxyEnableHttp2: proxy?.enable_http2 !== false,
    proxyFollowRedirects: proxy?.follow_redirects !== false,
    loginCheckUrl: loginConfig?.check_url || '',
    loginHeadersText: headersToText(loginConfig?.headers || {}),
    loginTimeout: loginConfig?.timeout ?? '',
    metadataNsfw: !!metadata?.nsfw,
    metadataRequiresCookies: !!metadata?.requires_cookies,
    metadataRequiresLogin: !!metadata?.requires_login,
    metadataOfflineThumbnailsDownload: !!metadata?.offline_thumbnails_download,
    metadataOfflineThumbnailsDisplay: !!metadata?.offline_thumbnails_display,
  }
}

export interface UseSiteConfigEditorFormOptions {
  visible: ComputedRef<boolean> | Ref<boolean>
  site: ComputedRef<LooseRecord | null> | Ref<LooseRecord | null>
  catalog: ComputedRef<LooseRecord> | Ref<LooseRecord>
  errorMessage: ComputedRef<string> | Ref<string>
  onSave: (payload: { slug: string; sitePayload: LooseRecord }) => void
}

export interface UseSiteConfigEditorFormReturn {
  siteEditorForm: Ref<SiteEditorForm>
  localError: Ref<string>
  resolvedError: ComputedRef<string>
  setSiteEditorBooleanField: (key: keyof SiteEditorForm, value: unknown) => void
  handleSave: () => void
}

export function useSiteConfigEditorForm(
  options: UseSiteConfigEditorFormOptions,
): UseSiteConfigEditorFormReturn {
  const { visible, site, catalog, errorMessage, onSave } = options

  const siteEditorForm = ref<SiteEditorForm>(createEmptyForm())
  const localError = ref('')

  const resolvedError = computed(() => localError.value || errorMessage.value)

  const setSiteEditorBooleanField = (key: keyof SiteEditorForm, value: unknown) => {
    if (!siteEditorForm.value || !key) return
    siteEditorForm.value[key] = !!value as never
  }

  const hydrateForm = () => {
    if (!site.value) {
      siteEditorForm.value = createEmptyForm()
      localError.value = ''
      return
    }
    siteEditorForm.value = buildFormFromSite(site.value, catalog.value)
    localError.value = ''
  }

  const handleSave = () => {
    localError.value = ''
    const { slug, siteName } = siteEditorForm.value
    if (!slug) {
      localError.value = '站点标识不可为空'
      return
    }

    const form = siteEditorForm.value
    const aliases = parseListInput(form.aliasesText)
    const label = form.label?.trim() || siteName || slug
    const httpHeaders = parseHeadersText(form.httpHeadersText)
    const loginHeaders = parseHeadersText(form.loginHeadersText)
    const rateLimitMin = toNumberOrUndefined(form.rateLimitMin)
    const rateLimitMax = toNumberOrUndefined(form.rateLimitMax)

    const proxyPayload: LooseRecord = {}
    const proxyFields: Array<[string, string]> = [
      ['connect_timeout', form.proxyConnectTimeout],
      ['read_timeout', form.proxyReadTimeout],
      ['write_timeout', form.proxyWriteTimeout],
      ['pool_timeout', form.proxyPoolTimeout],
      ['keepalive_expiry', form.proxyKeepaliveExpiry],
      ['max_connections', form.proxyMaxConnections],
      ['max_keepalive_connections', form.proxyMaxKeepaliveConnections],
      ['chunk_size', form.proxyChunkSize],
      ['max_retries', form.proxyMaxRetries],
    ]
    proxyFields.forEach(([key, value]) => {
      const num = toNumberOrUndefined(value)
      if (num !== undefined) proxyPayload[key] = num
    })
    proxyPayload.enable_http2 = !!form.proxyEnableHttp2
    proxyPayload.follow_redirects = !!form.proxyFollowRedirects

    const rateLimitPayload: LooseRecord = {}
    rateLimitPayload.enabled = !!form.rateLimitEnabled
    if (rateLimitMin !== undefined) rateLimitPayload.min_interval = rateLimitMin
    if (rateLimitMax !== undefined) rateLimitPayload.max_interval = rateLimitMax

    const loginPayload: LooseRecord = {}
    if (form.loginCheckUrl?.trim()) loginPayload.check_url = form.loginCheckUrl.trim()
    if (Object.keys(loginHeaders).length) loginPayload.headers = loginHeaders
    const loginTimeout = toNumberOrUndefined(form.loginTimeout)
    if (loginTimeout !== undefined) loginPayload.timeout = loginTimeout

    const sitePayload: LooseRecord = {
      label,
      aliases,
      enabled: !!form.enabled,
      metadata: {
        nsfw: !!form.metadataNsfw,
        requires_cookies: !!form.metadataRequiresCookies,
        requires_login: !!form.metadataRequiresLogin,
        offline_thumbnails_download: !!form.metadataOfflineThumbnailsDownload,
        offline_thumbnails_display: !!form.metadataOfflineThumbnailsDisplay,
      },
    }

    const testUrl = form.testUrl?.trim()
    if (testUrl) sitePayload.test_url = testUrl
    const iconUrl = form.iconUrl?.trim()
    if (iconUrl) sitePayload.icon_url = iconUrl
    if (Object.keys(httpHeaders).length) sitePayload.http = { headers: httpHeaders }
    if (Object.keys(rateLimitPayload).length) sitePayload.rate_limit = rateLimitPayload
    if (Object.keys(proxyPayload).some((key) => proxyPayload[key] !== undefined && proxyPayload[key] !== '')) {
      sitePayload.proxy = proxyPayload
    }
    if (Object.keys(loginPayload).length) sitePayload.login = loginPayload

    onSave({ slug, sitePayload })
  }

  // Re-hydrate on open, and reset on close so a stale form never lingers.
  watch(
    visible,
    (isVisible) => {
      if (!isVisible) {
        siteEditorForm.value = createEmptyForm()
        localError.value = ''
        return
      }
      hydrateForm()
    },
    { immediate: true },
  )

  // Re-hydrate when the underlying site/catalog change while open (e.g. editing
  // a different site, or a catalog refresh).
  watch(site, () => { if (visible.value) hydrateForm() }, { deep: true })
  watch(catalog, () => { if (visible.value) hydrateForm() }, { deep: true })

  return {
    siteEditorForm,
    localError,
    resolvedError,
    setSiteEditorBooleanField,
    handleSave,
  }
}
