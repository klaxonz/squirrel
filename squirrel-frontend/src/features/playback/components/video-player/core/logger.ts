export type PlayerLogger = {
  debug: (...args: unknown[]) => void
  info: (...args: unknown[]) => void
  warn: (...args: unknown[]) => void
  error: (...args: unknown[]) => void
}

const noop = () => {}

export const noopLogger: PlayerLogger = {
  debug: noop,
  info: noop,
  warn: noop,
  error: noop,
}

export const playerLogger: PlayerLogger = {
  debug: (...args: unknown[]) => console.debug('[SPPlayer]', ...args),
  info: (...args: unknown[]) => console.info('[SPPlayer]', ...args),
  warn: (...args: unknown[]) => console.warn('[SPPlayer]', ...args),
  error: (...args: unknown[]) => console.error('[SPPlayer]', ...args),
}
