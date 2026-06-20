/**
 * Pure presentation helpers for the SiteRuntimeManager view.
 *
 * Stateless formatters that map a runtime/enriched-runtime object (and a few
 * scalars) onto the badge text + Tailwind classes the template renders. Kept as
 * a composable so the view's script is free of half a dozen formulae interleaved
 * with the action handlers; each helper is a pure function of its argument.
 */

/** A runtime/enriched-runtime row. Typed loosely — the backend shape is dynamic
 *  and the helpers read a handful of optional fields off it. */
type RuntimeRow = Record<string, unknown>

const CAPABILITY_LABELS: Record<string, string> = {
  check_login_status: '登录检测',
  import_subscriptions: '导入订阅',
  resolve_subscription: '解析订阅',
  sync_subscription: '同步订阅',
  extract_video: '视频信息',
  fetch_subtitles: '字幕',
  resolve_proxy_config: '代理配置',
  rewrite_proxy_playlist: '代理播放',
}

export interface UseSiteRuntimeStatusReturn {
  getSiteRuntimeStatusText: (plugin: RuntimeRow) => string
  getSiteRuntimeStatusClass: (plugin: RuntimeRow) => string
  getNetworkText: (plugin: RuntimeRow) => string
  getLoginText: (plugin: RuntimeRow) => string
  getCapabilityLabel: (name: string) => string
  formatTime: (value: string | null | undefined) => string
}

export function useSiteRuntimeStatus(): UseSiteRuntimeStatusReturn {
  const getSiteRuntimeStatusText = (plugin: RuntimeRow): string => {
    if (!plugin.enabled) return '停用'
    const state = (plugin.active_runtime as Record<string, unknown> | undefined)?.state
    if (state === 'running') return '运行'
    const health = plugin.health as { healthy?: boolean } | undefined
    if (health?.healthy === false || state === 'failed') return '异常'
    return '待检查'
  }

  const getSiteRuntimeStatusClass = (plugin: RuntimeRow): string => {
    const state = (plugin.active_runtime as Record<string, unknown> | undefined)?.state
    if (!plugin.enabled) return 'border-border/50 bg-muted text-muted-foreground'
    if (state === 'running') return 'border-border/50 bg-background text-foreground'
    const health = plugin.health as { healthy?: boolean } | undefined
    if (health?.healthy === false || state === 'failed') {
      return 'border-destructive/20 bg-destructive/10 text-destructive'
    }
    return 'border-border/50 bg-muted text-muted-foreground'
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
      return loginStatus?.logged_in ? '桌面已登录' : '桌面未登录'
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

  return {
    getSiteRuntimeStatusText,
    getSiteRuntimeStatusClass,
    getNetworkText,
    getLoginText,
    getCapabilityLabel,
    formatTime,
  }
}
