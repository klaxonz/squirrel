import path from 'node:path'
import { app, BrowserWindow, clipboard, Menu, shell } from 'electron'
import {
  DEFAULT_WINDOW_STATE,
  bindWindowStatePersistence,
  loadWindowState,
} from './window-state.mjs'
import { closeCamoufoxDocumentLoader } from './document-loader.mjs'
import { showErrorShell, formatWindowTitle } from './shell-pages.mjs'
import { APP_NAME, __dirname } from './constants.mjs'

let rendererUrl = ''
let rendererOrigin = ''

export const setRendererOrigin = (url, origin) => {
  rendererUrl = url
  rendererOrigin = origin
}

const isTrustedNavigation = (targetUrl) => {
  try {
    return new URL(targetUrl).origin === rendererOrigin
  } catch {
    return false
  }
}

const navigateToRenderer = async (mainWindow) => {
  try {
    await mainWindow.loadURL(rendererUrl)
  } catch (error) {
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
      label: '后退',
      enabled: mainWindow.webContents.canGoBack(),
      click: () => mainWindow.webContents.goBack(),
    },
    {
      label: '前进',
      enabled: mainWindow.webContents.canGoForward(),
      click: () => mainWindow.webContents.goForward(),
    },
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
  const mainWindow = new BrowserWindow({
    x: windowState.x,
    y: windowState.y,
    width: windowState.width,
    height: windowState.height,
    minWidth: DEFAULT_WINDOW_STATE.minWidth,
    minHeight: DEFAULT_WINDOW_STATE.minHeight,
    show: false,
    title: APP_NAME,
    autoHideMenuBar: true,
    backgroundColor: '#091019',
    ...(isMac
      ? {
          titleBarStyle: 'hiddenInset',
        }
      : {
          frame: false,
          titleBarStyle: 'hidden',
        }),
    webPreferences: {
      preload: path.join(__dirname, 'preload.mjs'),
      contextIsolation: true,
      nodeIntegration: false,
      webSecurity: false,
    },
  })

  bindWindowStatePersistence(userDataPath, mainWindow)
  installMainWindowBehaviors(mainWindow)

  mainWindow.once('ready-to-show', () => {
    mainWindow.show()
  })
  mainWindow.on('closed', () => {
    void closeCamoufoxDocumentLoader()
  })

  if (windowState.isMaximized) {
    mainWindow.maximize()
  }

  void navigateToRenderer(mainWindow)
  return mainWindow
}

export { reloadRenderer, getDesktopWindowState }
