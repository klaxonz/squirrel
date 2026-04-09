import { ApiError, ErrorTypes } from './request'
import { logoutAndRedirect } from './auth'
import { Logger } from './logger'

type HandlerContext = Record<string, unknown>
type HandlerFn = (error: unknown, context: HandlerContext) => void

class ErrorHandler {
  private handlers = new Map<string, HandlerFn>()
  private fallbackHandler: HandlerFn | null = null

  register(type: string, handler: HandlerFn) {
    this.handlers.set(type, handler)
  }

  setFallbackHandler(handler: HandlerFn) {
    this.fallbackHandler = handler
  }

  handle(error: unknown, context: HandlerContext = {}) {
    Logger.debug('Error handled', error, context)

    if (error instanceof ApiError) {
      const handler = this.handlers.get(error.type)
      if (handler) {
        return handler(error, context)
      }
    }

    if (this.fallbackHandler) {
      return this.fallbackHandler(error, context)
    }

    this.defaultHandler(error, context)
  }

  defaultHandler(error: unknown, context: HandlerContext) {
    Logger.debug('Unhandled error', error, context)
  }
}

const globalErrorHandler = new ErrorHandler()

globalErrorHandler.register(ErrorTypes.UNAUTHORIZED, () => {
  logoutAndRedirect()
})

globalErrorHandler.register(ErrorTypes.NETWORK, (error) => {
  const message = typeof (error as any)?.message === 'string' ? (error as any).message : ''
  Logger.warn('Network error', message)
})

globalErrorHandler.register(ErrorTypes.SERVER_ERROR, (error) => {
  const message = typeof (error as any)?.message === 'string' ? (error as any).message : ''
  Logger.error('Server error', message)
})

export const vueErrorHandler = (error: unknown, instance: any, info: string) => {
  globalErrorHandler.handle(error, {
    component: instance?.$?.type?.name || 'Unknown',
    info,
    stack: (error as any)?.stack,
  })
}

export const unhandledRejectionHandler = (event: PromiseRejectionEvent) => {
  globalErrorHandler.handle(event.reason, {
    type: 'unhandledrejection',
    promise: event.promise,
  })
}
