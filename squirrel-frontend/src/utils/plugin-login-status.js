const DEFAULT_TITLE = 'Not logged in'

const containsAny = (text, tokens) => tokens.some(token => text.includes(token))

export const getLoginStatusBadge = (loginStatus) => {
  if (!loginStatus) {
    return {
      tone: 'muted',
      label: 'Untested',
      title: 'Login status has not been tested yet',
    }
  }

  const title = loginStatus.message || DEFAULT_TITLE
  if (loginStatus.logged_in) {
    return {
      tone: 'success',
      label: 'Valid',
      title,
    }
  }

  if (loginStatus.supported === false) {
    return {
      tone: 'danger',
      label: 'Error',
      title,
    }
  }

  const normalized = String(title).toLowerCase()

  if (containsAny(normalized, ['未找到', 'missing', 'not found'])) {
    return {
      tone: 'warning',
      label: 'Missing',
      title,
    }
  }

  if (containsAny(normalized, ['consent', 'challenge', '风控', 'not a bot', 'bot'])) {
    return {
      tone: 'danger',
      label: 'Blocked',
      title,
    }
  }

  if (containsAny(normalized, ['请求失败', 'error', 'failed', 'timeout', 'network'])) {
    return {
      tone: 'danger',
      label: 'Error',
      title,
    }
  }

  if (containsAny(normalized, ['未登录', '重定向', '登录页', 'expired', 'invalid'])) {
    return {
      tone: 'warning',
      label: 'Invalid',
      title,
    }
  }

  return {
    tone: 'warning',
    label: 'Invalid',
    title,
  }
}

export const shouldRefreshLoginStatusesAfterCookieImport = (payload) => {
  const sites = payload?.sites
  return Boolean(sites && typeof sites === 'object' && Object.keys(sites).length > 0)
}
