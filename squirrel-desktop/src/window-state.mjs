import fs from 'node:fs'
import path from 'node:path'

export const DEFAULT_WINDOW_STATE = {
  width: 1440,
  height: 960,
  minWidth: 1100,
  minHeight: 720,
}

const WINDOW_STATE_FILE_NAME = 'window-state.json'
const WINDOW_STATE_SAVE_DELAY_MS = 250

const getWindowStateFilePath = (userDataPath) => {
  return path.join(userDataPath, WINDOW_STATE_FILE_NAME)
}

const sanitizeDimension = (value, fallback, minimum) => {
  const numericValue = Number(value)
  if (!Number.isFinite(numericValue)) {
    return fallback
  }

  return Math.max(Math.round(numericValue), minimum)
}

const sanitizeCoordinate = (value) => {
  const numericValue = Number(value)
  return Number.isFinite(numericValue) ? Math.round(numericValue) : undefined
}

export const loadWindowState = (userDataPath) => {
  try {
    const rawState = fs.readFileSync(getWindowStateFilePath(userDataPath), 'utf8')
    const parsedState = JSON.parse(rawState)

    return {
      x: sanitizeCoordinate(parsedState.x),
      y: sanitizeCoordinate(parsedState.y),
      width: sanitizeDimension(parsedState.width, DEFAULT_WINDOW_STATE.width, DEFAULT_WINDOW_STATE.minWidth),
      height: sanitizeDimension(parsedState.height, DEFAULT_WINDOW_STATE.height, DEFAULT_WINDOW_STATE.minHeight),
      isMaximized: parsedState.isMaximized === true,
    }
  } catch {
    console.debug('[squirrel-desktop] window-state: loadWindowState failed, using defaults')
    return {
      width: DEFAULT_WINDOW_STATE.width,
      height: DEFAULT_WINDOW_STATE.height,
      isMaximized: false,
    }
  }
}

export const persistWindowState = (userDataPath, mainWindow) => {
  if (!mainWindow || mainWindow.isDestroyed() || mainWindow.isMinimized()) {
    return
  }

  const bounds = mainWindow.isMaximized()
    ? mainWindow.getNormalBounds()
    : mainWindow.getBounds()

  const state = {
    x: bounds.x,
    y: bounds.y,
    width: Math.max(bounds.width, DEFAULT_WINDOW_STATE.minWidth),
    height: Math.max(bounds.height, DEFAULT_WINDOW_STATE.minHeight),
    isMaximized: mainWindow.isMaximized(),
  }

  const filePath = getWindowStateFilePath(userDataPath)
  fs.mkdirSync(path.dirname(filePath), { recursive: true })
  fs.writeFileSync(filePath, JSON.stringify(state, null, 2), 'utf8')
}

export const bindWindowStatePersistence = (userDataPath, mainWindow) => {
  let saveTimer = null

  const scheduleSave = () => {
    if (saveTimer) {
      clearTimeout(saveTimer)
    }

    saveTimer = setTimeout(() => {
      persistWindowState(userDataPath, mainWindow)
      saveTimer = null
    }, WINDOW_STATE_SAVE_DELAY_MS)
  }

  mainWindow.on('resize', scheduleSave)
  mainWindow.on('move', scheduleSave)
  mainWindow.on('maximize', scheduleSave)
  mainWindow.on('unmaximize', scheduleSave)
  mainWindow.on('close', () => {
    if (saveTimer) {
      clearTimeout(saveTimer)
      saveTimer = null
    }
    persistWindowState(userDataPath, mainWindow)
  })
}
