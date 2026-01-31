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

