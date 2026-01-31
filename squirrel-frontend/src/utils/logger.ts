const LOG_LEVELS = {
  DEBUG: 10,
  INFO: 20,
  WARN: 30,
  ERROR: 40,
} as const

const resolveDefaultLevel = () => {
  return import.meta.env.DEV ? LOG_LEVELS.DEBUG : LOG_LEVELS.WARN
}

let currentLevel = resolveDefaultLevel()

const shouldLog = (level: number) => level >= currentLevel

const formatPrefix = (levelName: string) => {
  return `[${levelName}]`
}

export const setLogLevel = (levelName: unknown) => {
  const key = String(levelName || '').toUpperCase()
  if (!Object.prototype.hasOwnProperty.call(LOG_LEVELS, key)) return
  currentLevel = LOG_LEVELS[key as keyof typeof LOG_LEVELS]
}

export const Logger = {
  debug: (...args: unknown[]) => {
    if (!shouldLog(LOG_LEVELS.DEBUG)) return
    console.debug(formatPrefix('DEBUG'), ...args)
  },
  info: (...args: unknown[]) => {
    if (!shouldLog(LOG_LEVELS.INFO)) return
    console.info(formatPrefix('INFO'), ...args)
  },
  warn: (...args: unknown[]) => {
    if (!shouldLog(LOG_LEVELS.WARN)) return
    console.warn(formatPrefix('WARN'), ...args)
  },
  error: (...args: unknown[]) => {
    if (!shouldLog(LOG_LEVELS.ERROR)) return
    console.error(formatPrefix('ERROR'), ...args)
  },
}
