import { Logger } from '@/utils/logger'

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
  debug: (...args: unknown[]) => Logger.debug('[SPPlayer]', ...args),
  info: (...args: unknown[]) => Logger.info('[SPPlayer]', ...args),
  warn: (...args: unknown[]) => Logger.warn('[SPPlayer]', ...args),
  error: (...args: unknown[]) => Logger.error('[SPPlayer]', ...args),
}
