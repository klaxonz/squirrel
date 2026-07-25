const ALLOWED_WEB_CONTENT_PROTOCOLS = new Set(['http:', 'https:'])

// Electron only persists named partitions whose names start with "persist:".
export const WEB_CONTENT_SESSION_PARTITION = 'squirrel-rss-web-content'

const denyWindowOpen = Object.freeze({ action: 'deny' })
const hardenedWebContentSessions = new WeakSet()

export const normalizeWebContentUrl = (targetUrl) => {
  if (typeof targetUrl !== 'string') {
    return null
  }

  const candidate = targetUrl.trim()
  if (!candidate) {
    return null
  }

  try {
    const parsedUrl = new URL(candidate)
    if (!ALLOWED_WEB_CONTENT_PROTOCOLS.has(parsedUrl.protocol)) {
      return null
    }
    return parsedUrl.href
  } catch {
    return null
  }
}

const FRAME_OPTIONS_DENY = /(?:^|[,;\s])(?:DENY|SAMEORIGIN)(?:$|[,;\s])/i

const parseCspDirectives = (headerValue) => {
  if (typeof headerValue !== 'string' || !headerValue.trim()) return []
  return headerValue
    .split(',')
    .flatMap((policy) => policy.split(';'))
    .map((part) => part.trim())
    .filter(Boolean)
}

const cspAllowsFraming = (headerValue) => {
  const directives = parseCspDirectives(headerValue)
  const frameAncestors = directives.find((directive) => /^frame-ancestors\b/i.test(directive))
  if (!frameAncestors) return true

  const sources = frameAncestors
    .replace(/^frame-ancestors\b/i, '')
    .trim()
    .split(/\s+/)
    .filter(Boolean)

  if (sources.length === 0) return true
  if (sources.some((source) => source === '*' || source === 'https:' || source === 'http:')) return true
  // Any non-wildcard source list effectively blocks cross-origin app iframes.
  return false
}

export const evaluateFrameEmbeddability = (headers = {}, finalUrl = null) => {
  const normalized = {}
  for (const [key, value] of Object.entries(headers || {})) {
    if (value == null) continue
    normalized[String(key).toLowerCase()] = Array.isArray(value) ? value.join(', ') : String(value)
  }

  const xFrameOptions = normalized['x-frame-options']
  if (xFrameOptions && FRAME_OPTIONS_DENY.test(xFrameOptions)) {
    return {
      ok: true,
      embeddable: false,
      reason: 'x-frame-options',
      finalUrl: finalUrl || null,
      detail: xFrameOptions,
    }
  }

  const csp = normalized['content-security-policy'] || normalized['content-security-policy-report-only']
  if (csp && !cspAllowsFraming(csp)) {
    return {
      ok: true,
      embeddable: false,
      reason: 'csp-frame-ancestors',
      finalUrl: finalUrl || null,
      detail: csp,
    }
  }

  return {
    ok: true,
    embeddable: true,
    reason: null,
    finalUrl: finalUrl || null,
    detail: null,
  }
}

const headersToObject = (headers) => {
  if (!headers) return {}
  if (typeof headers.entries === 'function') {
    return Object.fromEntries(headers.entries())
  }
  if (typeof headers === 'object') return { ...headers }
  return {}
}

/**
 * Probe whether a remote article can be shown inside an app iframe.
 * Uses a lightweight GET so CDNs that only attach frame headers on full
 * responses still report correctly; body is discarded immediately.
 */
export const probeFrameEmbeddability = async (targetUrl, { fetchImpl = globalThis.fetch, timeoutMs = 8000 } = {}) => {
  const normalizedUrl = normalizeWebContentUrl(targetUrl)
  if (!normalizedUrl) {
    return {
      ok: false,
      embeddable: false,
      reason: 'invalid-url',
      finalUrl: null,
      detail: null,
    }
  }

  if (typeof fetchImpl !== 'function') {
    // Without a network probe, keep the optimistic path so non-desktop
    // environments can still attempt the iframe.
    return {
      ok: true,
      embeddable: true,
      reason: 'probe-unavailable',
      finalUrl: normalizedUrl,
      detail: null,
    }
  }

  const controller = typeof AbortController === 'function' ? new AbortController() : null
  const timer = controller
    ? setTimeout(() => controller.abort(), Math.max(1000, timeoutMs))
    : null

  try {
    const response = await fetchImpl(normalizedUrl, {
      method: 'GET',
      redirect: 'follow',
      signal: controller?.signal,
      headers: {
        Accept: 'text/html,application/xhtml+xml;q=0.9,*/*;q=0.8',
        // Prefer headers without downloading multi-MB article bodies.
        Range: 'bytes=0-0',
      },
    })

    // Drain/cancel body so keep-alive sockets free promptly.
    try {
      if (response.body && typeof response.body.cancel === 'function') {
        await response.body.cancel()
      } else if (typeof response.arrayBuffer === 'function') {
        await response.arrayBuffer()
      }
    } catch {
      // Ignore body cleanup failures; headers already decide embeddability.
    }

    return evaluateFrameEmbeddability(
      headersToObject(response.headers),
      response.url || normalizedUrl,
    )
  } catch (error) {
    return {
      ok: false,
      embeddable: true,
      reason: 'probe-failed',
      finalUrl: normalizedUrl,
      detail: error instanceof Error ? error.message : String(error),
    }
  } finally {
    clearTimeout(timer)
  }
}

export const hardenWebContentSession = (webContentSession) => {
  const hasSessionApi = webContentSession
    && (typeof webContentSession === 'object' || typeof webContentSession === 'function')
    && typeof webContentSession.setPermissionCheckHandler === 'function'
    && typeof webContentSession.setPermissionRequestHandler === 'function'
    && typeof webContentSession.on === 'function'

  if (!hasSessionApi) {
    throw new TypeError('webContentSession must be an Electron Session')
  }

  if (hardenedWebContentSessions.has(webContentSession)) {
    return webContentSession
  }

  webContentSession.setPermissionCheckHandler(() => false)
  webContentSession.setPermissionRequestHandler((_webContents, _permission, callback) => {
    callback(false)
  })
  webContentSession.on('will-download', (event) => {
    event.preventDefault()
  })
  hardenedWebContentSessions.add(webContentSession)

  return webContentSession
}

export const createWebContentSession = (sessionManager) => {
  if (!sessionManager || typeof sessionManager.fromPartition !== 'function') {
    throw new TypeError('sessionManager.fromPartition must be a function')
  }

  const webContentSession = sessionManager.fromPartition(
    WEB_CONTENT_SESSION_PARTITION,
    { cache: false },
  )
  return hardenWebContentSession(webContentSession)
}

export const createWebContentWindowOptions = (parentWindow, webContentSession) => {
  hardenWebContentSession(webContentSession)

  const hasUsableParent = parentWindow
    && typeof parentWindow.isDestroyed === 'function'
    && !parentWindow.isDestroyed()

  return {
    width: 1280,
    height: 820,
    minWidth: 720,
    minHeight: 480,
    show: false,
    autoHideMenuBar: true,
    ...(hasUsableParent ? { parent: parentWindow } : {}),
    webPreferences: {
      session: webContentSession,
      sandbox: true,
      contextIsolation: true,
      nodeIntegration: false,
      webSecurity: true,
      allowRunningInsecureContent: false,
    },
  }
}

const destroyWindow = (browserWindow) => {
  if (!browserWindow || browserWindow.isDestroyed()) {
    return
  }

  try {
    browserWindow.destroy()
  } catch {
    // The original startup error is more useful than a cleanup failure.
  }
}

export const createWebContentOpener = ({
  createWindow,
  openExternal,
  sessionManager,
  onError = (error) => console.error('[squirrel-desktop] Failed to open web content', error),
}) => {
  if (
    typeof createWindow !== 'function'
    || typeof openExternal !== 'function'
    || !sessionManager
    || typeof sessionManager.fromPartition !== 'function'
  ) {
    throw new TypeError('createWindow, openExternal, and sessionManager.fromPartition are required')
  }

  const openWindows = new Set()
  const reportError = (error) => {
    try {
      onError(error)
    } catch {
      // Error reporting must not change the bridge's boolean failure contract.
    }
  }

  const openWebContent = async (targetUrl, parentWindow) => {
    const normalizedUrl = normalizeWebContentUrl(targetUrl)
    if (!normalizedUrl) {
      return false
    }

    let browserWindow = null
    try {
      const webContentSession = createWebContentSession(sessionManager)
      browserWindow = createWindow(
        createWebContentWindowOptions(parentWindow, webContentSession),
      )
      openWindows.add(browserWindow)
      browserWindow.once('closed', () => openWindows.delete(browserWindow))

      const guardNavigation = (event, url) => {
        if (!normalizeWebContentUrl(url)) {
          event.preventDefault()
        }
      }
      browserWindow.webContents.on('will-navigate', guardNavigation)
      browserWindow.webContents.on('will-redirect', guardNavigation)

      browserWindow.webContents.setWindowOpenHandler(({ url }) => {
        const popupUrl = normalizeWebContentUrl(url)
        if (popupUrl) {
          void Promise.resolve()
            .then(() => openExternal(popupUrl))
            .catch(reportError)
        }
        return denyWindowOpen
      })

      await browserWindow.loadURL(normalizedUrl)
      if (browserWindow.isDestroyed()) {
        openWindows.delete(browserWindow)
        return false
      }

      browserWindow.show()
      return true
    } catch (error) {
      openWindows.delete(browserWindow)
      destroyWindow(browserWindow)
      reportError(error)
      return false
    }
  }

  return Object.freeze({ openWebContent })
}
