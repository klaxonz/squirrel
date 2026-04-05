const DEFAULT_TITLE = '未登录'

const containsAny = (text, tokens) => tokens.some(token => text.includes(token))

export const getLoginStatusBadge = (loginStatus) => {
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

  if (containsAny(normalized, ['请求失败', 'error', 'failed', 'timeout', 'network'])) {
    return {
      tone: 'danger',
      label: '错误',
      title,
    }
  }

  if (containsAny(normalized, ['未登录', '重定向', '登录页', 'expired', 'invalid'])) {
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

export const shouldRefreshLoginStatusesAfterCookieImport = (payload) => {
  const sites = payload?.sites
  return Boolean(sites && typeof sites === 'object' && Object.keys(sites).length > 0)
}
