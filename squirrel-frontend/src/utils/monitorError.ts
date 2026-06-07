import { Logger } from './logger'

export const monitorError = (context: string, error: unknown, level: 'warn' | 'error' = 'warn') => {
  Logger[level](`[${context}]`, error)
}
