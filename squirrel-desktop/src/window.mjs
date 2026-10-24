import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { app, BrowserWindow, clipboard, Menu, screen, shell } from 'electron'
import {
  DEFAULT_WINDOW_STATE,
  bindWindowStatePersistence,
  loadWindowState,
} from './window-state.mjs'
import { showErrorShell, formatWindowTitle } from './shell-pages.mjs'
import {
  APP_ICON_PATH,
  APP_NAME,
  __dirname,
  desktopChromeUserAgent,
  stripElectronFromUserAgent,
} from './constants.mjs'

let rendererUrl = ''
let rendererOrigin = ''
/** Absolute directory of packaged/dist index.html (renderer/dist). */
let rendererFileRoot = ''

const resolveRendererFileRoot = (url) => {
  if (!String(url || '').startsWith('file:')) {
    return ''
  }
  try {
    return path.normalize(path.dirname(fileURLToPath(url)))
  } catch {
    return ''
  }
}

export const setRendererOrigin = (url, origin) => {
  rendererUrl = url
  rendererOrigin = origin
  rendererFileRoot = resolveRendererFileRoot(url)
}

const isPathInsideDir = (filePath, dirPath) => {
  const normalizedFile = path.normalize(filePath)
  const normalizedDir = path.normalize(dirPath)
  const prefix = normalizedDir.endsWith(path.sep) ? normalizedDir : `${normalizedDir}${path.sep}`
  return normalizedFile === normalizedDir || normalizedFile.startsWith(prefix)
}

const isTrustedNavigation = (targetUrl) => {
  try {
    const target = new URL(targetUrl)
    // Packaged builds use file://; only trust the shipped renderer/dist tree.
    if (rendererUrl.startsWith('file:') || rendererOrigin === 'file://' || rendererOrigin === 'null') {
      if (target.protocol !== 'file:' || !rendererFileRoot) {
        return false
      }
      const targetPath = path.normalize(fileURLToPath(target))
      return isPathInsideDir(targetPath, rendererFileRoot)
    }
    return target.origin === rendererOrigin
  } catch {
    console.debug('[squirrel-desktop] window: isTrustedNavigation invalid URL', targetUrl)
    return false
  }
}

const isAbortLoadError = (error) => {
  const code = Number(error?.errno ?? error?.errorCode ?? error?.code)
  if (code === -3) {
    return true
  }

  const message = String(error?.message || error || '')
  return /ERR_ABORTED|error code -3/i.test(message)
}

const wait = (ms) => new Promise((resolve) => setTimeout(resolve, ms))

export const navigateToRenderer = async (mainWindow, attempt = 1) => {
  if (!mainWindow || mainWindow.isDestroyed()) {
    return
  }

  const maxAttempts = rendererUrl.startsWith('file:') ? 1 : 5

  try {
    if (rendererUrl.startsWith('file:')) {
      await mainWindow.loadFile(fileURLToPath(rendererUrl))
      return
    }
    await mainWindow.loadURL(rendererUrl)
  } catch (error) {
    // Chromium aborts in-flight navigations when another load supersedes them
    // (e.g. recovery shell, reload, or single-instance focus). Treat as non-fatal.
    if (isAbortLoadError(error)) {
      console.debug('[squirrel-desktop] Renderer load aborted (superseded)', {
        attempt,
        url: rendererUrl,
      })
      return
    }

    if (attempt < maxAttempts) {
      console.warn('[squirrel-desktop] Renderer load failed, retrying', {
        attempt,
        maxAttempts,
        error: error instanceof Error ? error.message : String(error),
      })
      await wait(400 * attempt)
      return navigateToRenderer(mainWindow, attempt + 1)
    }

    console.error('[squirrel-desktop] Failed to load renderer', error)
    await showErrorShell(mainWindow, {
      errorDescription: error instanceof Error ? error.message : 'Unknown load error',
      errorCode: 'LOAD_URL_FAILED',
    })
  }
}

const reloadRenderer = (mainWindow, ignoreCache = false) => {
  if (mainWindow.isDestroyed()) {
    return
  }

  const currentUrl = mainWindow.webContents.getURL()
  if (!isTrustedNavigation(currentUrl)) {
    void navigateToRenderer(mainWindow)
    return
  }

  if (ignoreCache) {
    mainWindow.webContents.reloadIgnoringCache()
    return
  }

  mainWindow.webContents.reload()
}

const getDesktopWindowState = (mainWindow) => {
  return {
    isMaximized: mainWindow?.isMaximized() === true,
  }
}

const sendDesktopWindowState = (mainWindow) => {
  if (!mainWindow || mainWindow.isDestroyed()) {
    return
  }

  mainWindow.webContents.send('desktop:window-state', getDesktopWindowState(mainWindow))
}

const buildContextMenuTemplate = (mainWindow, params) => {
  const template = []

  if (params.linkURL) {
    template.push(
      {
        label: '在浏览器中打开链接',
        click: () => {
          void shell.openExternal(params.linkURL)
        },
      },
      {
        label: '复制链接地址',
        click: () => clipboard.writeText(params.linkURL),
      },
      { type: 'separator' },
    )
  }

  if (params.isEditable) {
    template.push(
      { role: 'undo', label: '撤销' },
      { role: 'redo', label: '重做' },
      { type: 'separator' },
      { role: 'cut', label: '剪切' },
      { role: 'copy', label: '复制' },
      { role: 'paste', label: '粘贴' },
      { role: 'selectAll', label: '全选' },
    )
  } else if (String(params.selectionText || '').trim()) {
    template.push(
      { role: 'copy', label: '复制' },
      { role: 'selectAll', label: '全选' },
    )
  }

  template.push(
    { type: 'separator' },
    {
      label: '重新加载',
      click: () => reloadRenderer(mainWindow),
    },
  )

  if (!app.isPackaged) {
    template.push(
      { type: 'separator' },
      {
        label: '检查元素',
        click: () => mainWindow.webContents.inspectElement(params.x, params.y),
      },
    )
  }

  return template
}

const installMainWindowBehaviors = (mainWindow) => {
  const syncDesktopWindowState = () => {
    sendDesktopWindowState(mainWindow)
  }

  mainWindow.on('page-title-updated', (event, title) => {
    event.preventDefault()
    mainWindow.setTitle(formatWindowTitle(title))
  })

  mainWindow.on('maximize', syncDesktopWindowState)
  mainWindow.on('unmaximize', syncDesktopWindowState)
  mainWindow.on('app-command', (event, command) => {
    // 鼠标侧键 / 多媒体键触发的浏览器导航语义。Electron 不消费它，让 renderer
    // 端的 useNavigationHistory 统一处理（其内部含 enable/disable 判断，
    // 已是栈底就什么都不做）。
    if (command === 'browser-backward') {
      event.preventDefault()
      mainWindow.webContents.send('desktop:navigate', 'back')
      return
    }
    if (command === 'browser-forward') {
      event.preventDefault()
      mainWindow.webContents.send('desktop:navigate', 'forward')
      return
    }
    event.preventDefault()
  })
  mainWindow.webContents.on('did-finish-load', () => {
    syncDesktopWindowState()
  })

  mainWindow.webContents.on('before-input-event', (event, input) => {
    const key = String(input.key || '').toLowerCase()
    const isPrimaryModifier = input.control || input.meta
    const openDevTools =
      key === 'f12'
      || (isPrimaryModifier && input.shift && key === 'i')
      || (input.meta && input.alt && key === 'i')

    const reloadPage =
      key === 'f5'
      || (isPrimaryModifier && key === 'r')

    if (input.type !== 'keyDown') {
      return
    }

    if (reloadPage) {
      event.preventDefault()
      reloadRenderer(mainWindow, input.shift === true)
      return
    }

    if (!openDevTools) {
      return
    }

    event.preventDefault()
    if (mainWindow.webContents.isDevToolsOpened()) {
      mainWindow.webContents.closeDevTools()
      return
    }

    mainWindow.webContents.openDevTools({ mode: 'detach' })
  })

  mainWindow.webContents.on('context-menu', (event, params) => {
    const menu = Menu.buildFromTemplate(buildContextMenuTemplate(mainWindow, params))
    if (menu.items.length > 0) {
      menu.popup({ window: mainWindow })
    }
  })

  mainWindow.webContents.on('did-fail-load', (event, errorCode, errorDescription, validatedURL, isMainFrame) => {
    if (!isMainFrame || errorCode === -3 || String(validatedURL || '').startsWith('data:')) {
      return
    }

    void showErrorShell(mainWindow, { errorCode, errorDescription })
  })

  mainWindow.webContents.on('render-process-gone', (_event, details) => {
    console.error('[squirrel-desktop] Renderer process gone', {
      reason: details?.reason,
      exitCode: details?.exitCode,
      url: mainWindow.webContents.getURL(),
    })

    void showErrorShell(mainWindow, {
      errorCode: details.reason,
      errorDescription: 'Renderer process exited unexpectedly',
    })
  })

  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    if (isTrustedNavigation(url)) {
      return { action: 'allow' }
    }

    void shell.openExternal(url)
    return { action: 'deny' }
  })

  mainWindow.webContents.on('will-navigate', (event, url) => {
    if (isTrustedNavigation(url)) {
      return
    }

    event.preventDefault()
    void shell.openExternal(url)
  })
}

export const createMainWindow = () => {
  const userDataPath = app.getPath('userData')
  const windowState = loadWindowState(userDataPath)
  const isMac = process.platform === 'darwin'

  // A window saved at the full work area with isMaximized=false looks
  // maximized but has no reachable resize edge. Pull it back to a real
  // window size so it can be moved and resized.
  const { workArea } = screen.getPrimaryDisplay()
  const fillsWorkArea = (
    windowState.width >= workArea.width - 8
    && windowState.height >= workArea.height - 8
  )
  if (fillsWorkArea) {
    const width = Math.max(
      DEFAULT_WINDOW_STATE.minWidth,
      Math.min(DEFAULT_WINDOW_STATE.width, Math.round(workArea.width * 0.86)),
    )
    const height = Math.max(
      DEFAULT_WINDOW_STATE.minHeight,
      Math.min(DEFAULT_WINDOW_STATE.height, Math.round(workArea.height * 0.86)),
    )
    windowState.width = width
    windowState.height = height
    windowState.x = Math.round(workArea.x + (workArea.width - width) / 2)
    windowState.y = Math.round(workArea.y + (workArea.height - height) / 2)
  }

  let topmostClearedLogged = false
  const clearAlwaysOnTop = () => {
    if (mainWindow.isDestroyed()) {
      return
    }
    // Call unconditionally: a third-party window tool can set WS_EX_TOPMOST
    // without Electron's isAlwaysOnTop() flag reflecting it.
    mainWindow.setAlwaysOnTop(false)
    if (!topmostClearedLogged) {
      topmostClearedLogged = true
      console.info('[squirrel-desktop] window: always-on-top disabled')
    }
  }

  const mainWindow = new BrowserWindow({
    x: windowState.x,
    y: windowState.y,
    width: windowState.width,
    height: windowState.height,
    minWidth: DEFAULT_WINDOW_STATE.minWidth,
    minHeight: DEFAULT_WINDOW_STATE.minHeight,
    show: false,
    title: APP_NAME,
    icon: APP_ICON_PATH,
    autoHideMenuBar: true,
    backgroundColor: '#141110',
    resizable: true,
    movable: true,
    minimizable: true,
    maximizable: true,
    fullscreenable: true,
    ...(isMac
      ? {
          titleBarStyle: 'hiddenInset',
        }
      : {
          frame: false,
          titleBarStyle: 'hidden',
          thickFrame: true,
        }),
    webPreferences: {
      sandbox: false,
      preload: path.join(__dirname, 'preload.mjs'),
      contextIsolation: true,
      nodeIntegration: false,
      webSecurity: false,
      // Keep video decode / rAF running while the window is unfocused or
      // minimized, so the <video> element doesn't drop its last frame and
      // render black after regaining visibility.
      backgroundThrottling: false,
    },
  })

  bindWindowStatePersistence(userDataPath, mainWindow)
  installMainWindowBehaviors(mainWindow)

  clearAlwaysOnTop()
  mainWindow.on('focus', clearAlwaysOnTop)
  mainWindow.on('blur', clearAlwaysOnTop)
  mainWindow.on('restore', clearAlwaysOnTop)
  mainWindow.on('show', clearAlwaysOnTop)

  // FreeTube: Chrome UA without Electron token on the main webContents.
  // Session-level setUserAgent alone is not always inherited by every request.
  try {
    const fixedUa = stripElectronFromUserAgent(
      mainWindow.webContents.getUserAgent?.() || desktopChromeUserAgent,
      APP_NAME,
    ) || desktopChromeUserAgent
    mainWindow.webContents.setUserAgent(fixedUa)
  } catch (err) {
    console.debug('[squirrel-desktop] window: setUserAgent failed', err)
  }

  mainWindow.once('ready-to-show', () => {
    clearAlwaysOnTop()
    mainWindow.show()
  })
  if (windowState.isMaximized) {
    mainWindow.maximize()
  }

  void navigateToRenderer(mainWindow)
  return mainWindow
}

/**
 * Focus recovery for second-instance / activate: only reload when the window
 * left the trusted renderer origin (or loadFile tree).
 */
export const ensureRendererLoaded = (mainWindow) => {
  if (!mainWindow || mainWindow.isDestroyed()) {
    return
  }

  try {
    const currentUrl = mainWindow.webContents.getURL()
    if (currentUrl && isTrustedNavigation(currentUrl)) {
      return
    }
  } catch {
    // Fall through and force a trusted navigation.
  }

  void navigateToRenderer(mainWindow)
}

export { reloadRenderer, getDesktopWindowState }
