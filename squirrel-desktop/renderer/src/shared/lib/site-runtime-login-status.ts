// ponytail: login status shape is aggregated from site-runtime backends and
// varies per-site; only the fields this module reads are typed here.
export interface SiteLoginStatus {
  logged_in?: boolean
  supported?: boolean
  message?: string
  extra?: { transient_failure?: boolean } & Record<string, unknown>
  oauth_status?: unknown
  oauth_account?: unknown
}

export interface StatusBadge {
  tone: 'muted' | 'success' | 'warning' | 'danger'
  label: string
  title: string
}

interface CookieImportPayload {
  sites?: Record<string, unknown>
}

const DEFAULT_TITLE = '未登录'

const containsAny = (text: string, tokens: string[]): boolean => tokens.some((token) => text.includes(token))

const TRANSIENT_FAILURE_TOKENS = [
  '检测失败',
  '请求失败',
  'timeout',
  'network',
  'gateway',
  'upstream',
  '5xx',
  '502',
  '503',
  '504',
  '站点错误页',
]

const isTransientLoginFailure = (loginStatus: SiteLoginStatus | null | undefined): boolean => {
  if (!loginStatus || loginStatus.logged_in) {
    return false
  }

  if (loginStatus.extra?.transient_failure === true) {
    return true
  }

  const title = String(loginStatus.message || '').toLowerCase()
  return containsAny(title, TRANSIENT_FAILURE_TOKENS)
}

export const getLoginStatusBadge = (loginStatus: SiteLoginStatus | null | undefined): StatusBadge => {
  if (!loginStatus) {
    return {
      tone: 'muted',
      label: '未测试',
      title: '尚未进行登录状态检测',
    }
  }

  const title = loginStatus.message || DEFAULT_TITLE
  if (loginStatus.logged_in) {
    return {
      tone: 'success',
      label: '有效',
      title,
    }
  }

  if (loginStatus.supported === false) {
    return {
      tone: 'danger',
      label: '错误',
      title,
    }
  }

  const normalized = String(title).toLowerCase()

  if (containsAny(normalized, ['未找到', 'missing', 'not found'])) {
    return {
      tone: 'warning',
      label: '缺失',
      title,
    }
  }

  if (containsAny(normalized, ['consent', 'challenge', '风控', 'not a bot', 'bot'])) {
    return {
      tone: 'danger',
      label: '已拦截',
      title,
    }
  }

  if (isTransientLoginFailure(loginStatus) || containsAny(normalized, ['error', 'failed'])) {
    return {
      tone: 'danger',
      label: '错误',
      title,
    }
  }

  if (containsAny(normalized, ['未登录', '重定向', '登录页'])) {
    return {
      tone: 'warning',
      label: '未登录',
      title,
    }
  }

  if (containsAny(normalized, ['expired', 'invalid'])) {
    return {
      tone: 'warning',
      label: '无效',
      title,
    }
  }

  return {
    tone: 'warning',
    label: '无效',
    title,
  }
}

export const mergeLoginStatusResult = (
  previousStatus: SiteLoginStatus | null | undefined,
  nextStatus: SiteLoginStatus | null | undefined,
): SiteLoginStatus | null | undefined => {
  if (!nextStatus) {
    return previousStatus
  }

  if (previousStatus?.logged_in && isTransientLoginFailure(nextStatus)) {
    return previousStatus
  }

  return nextStatus
}

export const shouldRefreshLoginStatusesAfterCookieImport = (
  payload: CookieImportPayload | null | undefined,
): boolean => {
  const sites = payload?.sites
  return Boolean(sites && typeof sites === 'object' && Object.keys(sites).length > 0)
}
