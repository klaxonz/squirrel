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
