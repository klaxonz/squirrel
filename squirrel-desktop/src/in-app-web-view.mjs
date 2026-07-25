import {
  createWebContentSession,
  normalizeWebContentUrl,
} from './web-content-window.mjs'

const denyWindowOpen = Object.freeze({ action: 'deny' })

const normalizeBounds = (bounds) => {
  if (!bounds || typeof bounds !== 'object') return null
  const x = Math.round(Number(bounds.x))
  const y = Math.round(Number(bounds.y))
  const width = Math.round(Number(bounds.width))
  const height = Math.round(Number(bounds.height))
  if (![x, y, width, height].every(Number.isFinite)) return null
  if (width <= 0 || height <= 0) return null
  return { x, y, width, height }
}

const destroyView = (view) => {
  if (!view) return
  try {
    const webContents = view.webContents
    if (webContents && !webContents.isDestroyed?.()) {
      webContents.close?.()
    }
  } catch {
    // Best-effort cleanup.
  }
}

/**
 * Embeds remote article pages inside the main window via WebContentsView.
 * Unlike <iframe>, this is top-level navigation so X-Frame-Options / CSP
 * frame-ancestors do not blank the page — and it never leaves the app shell.
 */
export const createInAppWebViewController = ({
  createWebContentsView,
  sessionManager,
  openExternal,
  onError = (error) => console.error('[squirrel-desktop] in-app web view failed', error),
}) => {
  if (
    typeof createWebContentsView !== 'function'
    || !sessionManager
    || typeof sessionManager.fromPartition !== 'function'
    || typeof openExternal !== 'function'
  ) {
    throw new TypeError('createWebContentsView, sessionManager, and openExternal are required')
  }

  let active = null

  const reportError = (error) => {
    try {
      onError(error)
    } catch {
      // Keep the bridge boolean contract stable.
    }
  }

  const detach = (entry = active) => {
    if (!entry) return
    const { view, parentWindow } = entry
    try {
      parentWindow?.contentView?.removeChildView?.(view)
    } catch {
      // Parent may already be destroyed.
    }
    destroyView(view)
    if (active === entry) active = null
  }

  const ensureAttached = (parentWindow) => {
    if (!parentWindow || parentWindow.isDestroyed?.()) {
      throw new Error('Parent window is unavailable')
    }

    if (active?.parentWindow === parentWindow && active.view) {
      return active
    }

    detach()

    const webContentSession = createWebContentSession(sessionManager)
    const view = createWebContentsView({
      webPreferences: {
        session: webContentSession,
        sandbox: true,
        contextIsolation: true,
        nodeIntegration: false,
        webSecurity: true,
        allowRunningInsecureContent: false,
      },
    })

    const guardNavigation = (event, url) => {
      if (!normalizeWebContentUrl(url)) event.preventDefault()
    }
    view.webContents.on('will-navigate', guardNavigation)
    view.webContents.on('will-redirect', guardNavigation)
    view.webContents.setWindowOpenHandler(({ url }) => {
      const popupUrl = normalizeWebContentUrl(url)
      if (popupUrl) {
        void Promise.resolve()
          .then(() => openExternal(popupUrl))
          .catch(reportError)
      }
      return denyWindowOpen
    })

    parentWindow.contentView.addChildView(view)
    parentWindow.once?.('closed', () => {
      if (active?.parentWindow === parentWindow) detach()
    })

    active = {
      view,
      parentWindow,
      ownerId: parentWindow.id,
      url: null,
    }
    return active
  }

  const open = async (parentWindow, targetUrl, bounds) => {
    const normalizedUrl = normalizeWebContentUrl(targetUrl)
    const normalizedBounds = normalizeBounds(bounds)
    if (!normalizedUrl || !normalizedBounds) return false

    try {
      const entry = ensureAttached(parentWindow)
      entry.view.setBounds(normalizedBounds)
      entry.view.setVisible?.(true)
      if (entry.url !== normalizedUrl) {
        await entry.view.webContents.loadURL(normalizedUrl)
        entry.url = normalizedUrl
      }
      if (parentWindow.isDestroyed?.() || entry.view.webContents.isDestroyed?.()) {
        detach(entry)
        return false
      }
      return true
    } catch (error) {
      detach()
      reportError(error)
      return false
    }
  }

  const setBounds = (parentWindow, bounds) => {
    if (!active || active.parentWindow !== parentWindow) return false
    const normalizedBounds = normalizeBounds(bounds)
    if (!normalizedBounds) return false
    try {
      active.view.setBounds(normalizedBounds)
      return true
    } catch (error) {
      reportError(error)
      return false
    }
  }

  const reload = async (parentWindow) => {
    if (!active || active.parentWindow !== parentWindow || !active.url) return false
    try {
      active.view.webContents.reload()
      return true
    } catch (error) {
      reportError(error)
      return false
    }
  }

  const hide = (parentWindow) => {
    if (!active) return true
    if (parentWindow && active.parentWindow !== parentWindow) return false
    detach()
    return true
  }

  return Object.freeze({
    open,
    setBounds,
    reload,
    hide,
  })
}
