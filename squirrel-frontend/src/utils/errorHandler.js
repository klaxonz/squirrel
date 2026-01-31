import { ApiError, ErrorTypes } from './request'
import { logoutAndRedirect } from './auth'
import { Logger } from './logger'

/**
 * 全局错误处理器
 */
export class ErrorHandler {
  constructor() {
    this.handlers = new Map()
    this.fallbackHandler = null
  }

  /**
   * 注册错误处理器
   */
  register(type, handler) {
    this.handlers.set(type, handler)
  }

  /**
   * 设置默认错误处理器
   */
  setFallbackHandler(handler) {
    this.fallbackHandler = handler
  }

  /**
   * 处理错误
   */
  handle(error, context = {}) {
    Logger.debug('Error handled', error, context)

    // 如果是 ApiError，使用对应的处理器
    if (error instanceof ApiError) {
      const handler = this.handlers.get(error.type)
      if (handler) {
        return handler(error, context)
      }
    }

    // 使用默认处理器
    if (this.fallbackHandler) {
      return this.fallbackHandler(error, context)
    }

    // 默认错误处理
    this.defaultHandler(error, context)
  }

  /**
   * 默认错误处理器
   */
  defaultHandler(error, context) {
    Logger.debug('Unhandled error', error, context)
  }
}

// 创建全局错误处理器实例
export const globalErrorHandler = new ErrorHandler()

// 注册默认错误处理器
globalErrorHandler.register(ErrorTypes.UNAUTHORIZED, (error) => {
  // 处理未授权错误 - 跳转到登录页
  logoutAndRedirect()
})

globalErrorHandler.register(ErrorTypes.NETWORK, (error) => {
  // 处理网络错误 - 显示重试选项
  Logger.warn('Network error', error.message)
  // 可以触发全局的重试机制或显示网络错误提示
})

globalErrorHandler.register(ErrorTypes.SERVER_ERROR, (error) => {
  // 处理服务器错误
  Logger.error('Server error', error.message)
  // 可以显示服务器错误提示
})

/**
 * Vue 错误处理函数
 */
export const vueErrorHandler = (error, instance, info) => {
  globalErrorHandler.handle(error, {
    component: instance?.$?.type?.name || 'Unknown',
    info,
    stack: error.stack,
  })
}

/**
 * Promise 拒绝处理函数
 */
export const unhandledRejectionHandler = (event) => {
  globalErrorHandler.handle(event.reason, {
    type: 'unhandledrejection',
    promise: event.promise,
  })
}

/**
 * 工具函数：安全执行异步函数
 */
export const safeAsync = async (fn, errorContext = {}) => {
  try {
    return await fn()
  } catch (error) {
    globalErrorHandler.handle(error, errorContext)
    throw error
  }
}

/**
 * 工具函数：包装 composable 函数
 */
export const withErrorHandling = (composableFn) => {
  return (...args) => {
    try {
      const result = composableFn(...args)

      // 如果返回的是函数（可能是 setup 函数），包装它
      if (typeof result === 'function') {
        return (...setupArgs) => {
          try {
            return result(...setupArgs)
          } catch (error) {
            globalErrorHandler.handle(error, { composable: composableFn.name })
            throw error
          }
        }
      }

      return result
    } catch (error) {
      globalErrorHandler.handle(error, { composable: composableFn.name })
      throw error
    }
  }
}
