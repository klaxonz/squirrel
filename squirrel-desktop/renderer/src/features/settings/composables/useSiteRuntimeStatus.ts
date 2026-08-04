/**
 * Pure presentation helpers for the SiteRuntimeManager view.
 *
 * Stateless formatters that map an enriched site row (and a few scalars) onto
 * the badge text + Tailwind classes the template renders. Kept as a composable
 * so the view's script is free of half a dozen formulae interleaved with the
 * action handlers; each helper is a pure function of its argument.
 *
 * Post site-plugin refactor: rows are `GET /api/sites` entries enriched with
 * connectivity/login results. Plugin status fields (active_runtime/health) are
 * gone — the network + account signals carry the real operational state.
 */

/** A site row. Typed loosely — the backend shape is dynamic and the helpers
 *  read a handful of optional fields off it. */
type RuntimeRow = Record<string, unknown>

const CAPABILITY_LABELS: Record<string, string> = {
  check_login_status: '登录检测',
  import_subscriptions: '导入订阅',
  resolve_subscription: '解析订阅',
  sync_subscription: '同步订阅',
  extract_video: '视频信息',
}

/** Visual tone for operational readiness — success ≠ brand primary (DESIGN §2). */
export type SiteRuntimeTone = 'success' | 'muted' | 'critical'

export interface UseSiteRuntimeStatusReturn {
  getNetworkText: (plugin: RuntimeRow) => string
  getNetworkVariant: (plugin: RuntimeRow) => SiteRuntimeTone
  getLoginText: (plugin: RuntimeRow) => string
  getLoginVariant: (plugin: RuntimeRow) => SiteRuntimeTone
  getCapabilityLabel: (name: string) => string
  formatTime: (value: string | null | undefined) => string
  supportsLogin: (plugin: RuntimeRow) => boolean
  isConnected: (plugin: RuntimeRow) => boolean
  needsAttention: (plugin: RuntimeRow) => boolean
}

export function useSiteRuntimeStatus(): UseSiteRuntimeStatusReturn {
  const getNetworkVariant = (plugin: RuntimeRow): SiteRuntimeTone => {
    if (plugin.siteAccessible === true) return 'success'
    if (plugin.siteAccessible === false) return 'critical'
    return 'muted'
  }

  const getLoginVariant = (plugin: RuntimeRow): SiteRuntimeTone => {
    if (plugin.siteOAuthStatus === 'authenticated') return 'success'
    if (plugin.siteOAuthStatus === 'pending') return 'muted'
    const loginStatus = plugin.siteLoginStatus as Record<string, unknown> | undefined
    if (loginStatus?.supported === false) return 'muted'
    if (loginStatus?.logged_in) return 'success'
    if (loginStatus) return 'critical'
    return 'muted'
  }

  const getNetworkText = (plugin: RuntimeRow): string => {
    if (plugin.siteAccessible === true) return '正常'
    if (plugin.siteAccessible === false) return '失败'
    return '未检测'
  }

  const getLoginText = (plugin: RuntimeRow): string => {
    if (plugin.siteOAuthStatus === 'authenticated') return '有效'
    if (plugin.siteOAuthStatus === 'pending') return '授权中'
    const loginStatus = plugin.siteLoginStatus as Record<string, unknown> | undefined
    if (loginStatus?.supported === false) return '不支持'
    if (loginStatus?.source === 'desktop') {
      return loginStatus?.logged_in ? '已登录' : '未登录'
    }
    if (loginStatus?.logged_in) return '有效'
    if (loginStatus) return '失效'
    return '未检测'
  }

  const getCapabilityLabel = (name: string): string => CAPABILITY_LABELS[name] || name

  const formatTime = (value: string | null | undefined): string => {
    if (!value) return '—'
    return new Date(value).toLocaleString('zh-CN', {
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
    })
  }

  const supportsLogin = (plugin: RuntimeRow): boolean => Boolean(
    plugin.siteSupportsLogin
    || plugin.siteDesktopLoginSupported
    || plugin.siteName === 'youtube',
  )

  const isConnected = (plugin: RuntimeRow): boolean => (
    plugin.siteOAuthStatus === 'authenticated'
    || Boolean((plugin.siteLoginStatus as Record<string, unknown> | undefined)?.logged_in)
  )

  /** Enabled sources only need attention once a real failure is known. */
  const needsAttention = (plugin: RuntimeRow): boolean => {
    if (!plugin.enabled) return false
    if (plugin.siteAccessible === false) return true

    const loginStatus = plugin.siteLoginStatus as Record<string, unknown> | undefined
    if (!supportsLogin(plugin) || !loginStatus) return false
    return plugin.siteOAuthStatus !== 'authenticated'
      && plugin.siteOAuthStatus !== 'pending'
      && !loginStatus.logged_in
  }

  return {
    getNetworkText,
    getNetworkVariant,
    getLoginText,
    getLoginVariant,
    getCapabilityLabel,
    formatTime,
    supportsLogin,
    isConnected,
    needsAttention,
  }
}
