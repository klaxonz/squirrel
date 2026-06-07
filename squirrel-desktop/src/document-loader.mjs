import path from 'node:path'
import { app, BrowserWindow, session } from 'electron'
import { CamoufoxDocumentLoader } from './cloudflare/camoufox-document-loader.mjs'
import { getCookieProfileForUrl } from './site-login.mjs'
import { normalizeTargetUrl, isJavdbCookieTarget, isMissavDocumentTarget } from './cookie-header.mjs'
import { desktopChromeUserAgent, DOCUMENT_READ_TIMEOUT_MS } from './constants.mjs'

export const createSessionFetch = () => {
  return async (targetUrl, options = {}) => {
    const abortController = new AbortController()
    const timeoutMs = Number(options?.timeoutMs) || 25000
    const timer = setTimeout(() => abortController.abort(), timeoutMs)

    try {
      return await session.defaultSession.fetch(targetUrl, {
        method: options?.method || 'GET',
        headers: options?.headers || {},
        body: options?.body,
        redirect: options?.redirect || 'follow',
        signal: abortController.signal,
      })
    } finally {
      clearTimeout(timer)
    }
  }
}

let camoufoxDocumentLoader = null

const getCamoufoxDocumentLoader = () => {
  if (!camoufoxDocumentLoader) {
    camoufoxDocumentLoader = new CamoufoxDocumentLoader({
      electronSession: session.defaultSession,
      userDataDir: path.join(app.getPath('userData'), 'camoufox-documents'),
    })
  }
  return camoufoxDocumentLoader
}

export const closeCamoufoxDocumentLoader = async () => {
  const loader = camoufoxDocumentLoader
  camoufoxDocumentLoader = null
  if (loader) {
    await loader.close()
  }
}

const waitForDocumentNavigation = async (browserWindow, targetUrl, userAgent, timeoutMs) => {
  let settled = false
  let timer

  await new Promise((resolve, reject) => {
    const cleanup = () => {
      browserWindow.webContents.off('dom-ready', handleReady)
      browserWindow.webContents.off('did-finish-load', handleReady)
      browserWindow.webContents.off('did-fail-load', handleFail)
      clearTimeout(timer)
    }
    const finish = (callback, value) => {
      if (settled) return
      settled = true
      cleanup()
      callback(value)
    }
    const handleReady = () => finish(resolve)
    const handleFail = (_event, errorCode, errorDescription) => {
      finish(reject, new Error(`Document load failed: ${errorCode} ${errorDescription}`))
    }

    browserWindow.webContents.once('dom-ready', handleReady)
    browserWindow.webContents.once('did-finish-load', handleReady)
    browserWindow.webContents.once('did-fail-load', handleFail)
    timer = setTimeout(() => finish(reject, new Error('Document load timed out')), timeoutMs)

    browserWindow.loadURL(targetUrl, { userAgent }).catch((error) => {
      finish(reject, error)
    })
  })
}

const readBrowserWindowHtml = async (browserWindow) => {
  let timer
  try {
    const html = await Promise.race([
      browserWindow.webContents.executeJavaScript('document.documentElement.outerHTML', true),
      new Promise((_, reject) => {
        timer = setTimeout(() => reject(new Error('Document read timed out')), DOCUMENT_READ_TIMEOUT_MS)
      }),
    ])
    return String(html || '')
  } finally {
    clearTimeout(timer)
  }
}

const readBrowserWindowValue = async (browserWindow, script, timeoutMs = DOCUMENT_READ_TIMEOUT_MS) => {
  let timer
  try {
    return await Promise.race([
      browserWindow.webContents.executeJavaScript(script, true),
      new Promise((_, reject) => {
        timer = setTimeout(() => reject(new Error('Document script timed out')), timeoutMs)
      }),
    ])
  } finally {
    clearTimeout(timer)
  }
}

const createDocumentBrowserWindow = async (profile) => {
  const documentWindow = new BrowserWindow({
    width: 1280,
    height: 900,
    show: false,
    paintWhenInitiallyHidden: true,
    webPreferences: {
      session: session.defaultSession,
      nodeIntegration: false,
      contextIsolation: true,
      sandbox: true,
      backgroundThrottling: false,
    },
  })

  const userAgent = profile?.userAgent || desktopChromeUserAgent
  documentWindow.webContents.setUserAgent(userAgent)

  return { documentWindow, userAgent }
}

const loadDocumentHtmlWithBrowserWindowOnce = async (normalizedUrl, options = {}) => {
  const profile = getCookieProfileForUrl(normalizedUrl)
  const timeoutMs = Number(options?.timeoutMs) || 30000

  const { documentWindow, userAgent } = await createDocumentBrowserWindow(profile)

  try {
    await waitForDocumentNavigation(documentWindow, normalizedUrl, userAgent, timeoutMs)
    if (typeof options?.evaluatePage === 'function') {
      const value = await options.evaluatePage((script) => readBrowserWindowValue(documentWindow, script, timeoutMs))
      await session.defaultSession.cookies.flushStore()
      return value
    }
    if (typeof options?.evaluateScript === 'string' && options.evaluateScript.trim()) {
      const value = await readBrowserWindowValue(documentWindow, options.evaluateScript, timeoutMs)
      await session.defaultSession.cookies.flushStore()
      return value
    }
    const html = await readBrowserWindowHtml(documentWindow)
    await session.defaultSession.cookies.flushStore()
    return String(html || '')
  } finally {
    if (!documentWindow.isDestroyed() && documentWindow.webContents.isLoading()) {
      documentWindow.webContents.stop()
    }
    if (!documentWindow.isDestroyed()) {
      documentWindow.close()
    }
  }
}

export const loadDocumentHtmlWithBrowserWindow = async (targetUrl, options = {}) => {
  const normalizedUrl = normalizeTargetUrl(targetUrl)
  if (!normalizedUrl) {
    throw new Error('Invalid document URL')
  }

  if (isJavdbCookieTarget(normalizedUrl) || isMissavDocumentTarget(normalizedUrl)) {
    return getCamoufoxDocumentLoader().loadHtml(normalizedUrl, {
      timeoutMs: options?.timeoutMs,
      challengeTimeoutMs: options?.challengeTimeoutMs,
    })
  }

  return loadDocumentHtmlWithBrowserWindowOnce(normalizedUrl, options)
}
