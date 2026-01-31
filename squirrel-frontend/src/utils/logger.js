const LOG_LEVELS = {
  DEBUG: 10,
  INFO: 20,
  WARN: 30,
  ERROR: 40,
}

const resolveDefaultLevel = () => {
  return import.meta.env.DEV ? LOG_LEVELS.DEBUG : LOG_LEVELS.WARN
}

let currentLevel = resolveDefaultLevel()

const shouldLog = (level) => level >= currentLevel

const formatPrefix = (levelName) => {
  return `[${levelName}]`
}

export const setLogLevel = (levelName) => {
  const key = String(levelName || '').toUpperCase()
  if (!Object.prototype.hasOwnProperty.call(LOG_LEVELS, key)) return
  currentLevel = LOG_LEVELS[key]
}

export const Logger = {
  debug: (...args) => {
    if (!shouldLog(LOG_LEVELS.DEBUG)) return
    console.debug(formatPrefix('DEBUG'), ...args)
  },
  info: (...args) => {
    if (!shouldLog(LOG_LEVELS.INFO)) return
    console.info(formatPrefix('INFO'), ...args)
  },
  warn: (...args) => {
    if (!shouldLog(LOG_LEVELS.WARN)) return
    console.warn(formatPrefix('WARN'), ...args)
  },
  error: (...args) => {
    if (!shouldLog(LOG_LEVELS.ERROR)) return
    console.error(formatPrefix('ERROR'), ...args)
  },
}

