import type { AxiosRequestConfig, AxiosResponse } from 'axios'
import axios from './axios'

export const ErrorTypes = {
  CANCELED: 'CANCELED',
  NETWORK: 'NETWORK',
  API: 'API',
  TIMEOUT: 'TIMEOUT',
  UNAUTHORIZED: 'UNAUTHORIZED',
  FORBIDDEN: 'FORBIDDEN',
  NOT_FOUND: 'NOT_FOUND',
  SERVER_ERROR: 'SERVER_ERROR',
  UNKNOWN: 'UNKNOWN',
} as const

export type ErrorType = typeof ErrorTypes[keyof typeof ErrorTypes]

type ApiEnvelope<T = unknown> = {
  code: number
  msg?: string
  data?: T
}

export type RequestResult<T = any> = {
  data: T | null
  error: ApiError | null
}

export class ApiError extends Error {
  type: ErrorType
  status: number | null
  data: unknown | null

  constructor(message: string, type: ErrorType = ErrorTypes.UNKNOWN, status: number | null = null, data: unknown | null = null) {
    super(message)
    this.name = 'ApiError'
    this.type = type
    this.status = status
    this.data = data
  }
}

const isApiEnvelope = (data: any): data is ApiEnvelope => {
  return !!data && typeof data.code === 'number'
}
const getErrorType = (error: any): ErrorType => {
  if (error?.code === 'ERR_CANCELED') {
    return ErrorTypes.CANCELED
  }

  if (!error.response) {
    if (error.code === 'ECONNABORTED') return ErrorTypes.TIMEOUT
    return ErrorTypes.NETWORK
  }

  const status = error.response.status
  switch (status) {
    case 401: return ErrorTypes.UNAUTHORIZED
    case 403: return ErrorTypes.FORBIDDEN
    case 404: return ErrorTypes.NOT_FOUND
    case 500:
    case 502:
    case 503: return ErrorTypes.SERVER_ERROR
    default: return ErrorTypes.API
  }
}
const formatErrorMessage = (error: any) => {
  if (error.response?.data?.msg) {
    return error.response.data.msg
  }

  switch (getErrorType(error)) {
    case ErrorTypes.CANCELED: return '请求已取消'
    case ErrorTypes.NETWORK: return '网络连接失败，请检查网络设置'
    case ErrorTypes.TIMEOUT: return '请求超时，请稍后重试'
    case ErrorTypes.UNAUTHORIZED: return '登录已过期，请重新登录'
    case ErrorTypes.FORBIDDEN: return '权限不足'
    case ErrorTypes.NOT_FOUND: return '请求的资源不存在'
    case ErrorTypes.SERVER_ERROR: return '服务器错误，请稍后重试'
    default: return '请求失败，请稍后重试'
  }
}
export const handleRequest = async <T = any>(promise: Promise<AxiosResponse<any>>): Promise<RequestResult<T>> => {
  try {
    const response = await promise

    if (isApiEnvelope(response.data)) {
      if (response.data.code === 0) {
        return {
          data: (response.data.data ?? null) as T | null,
          error: null,
        }
      }

      const error = new ApiError(
        response.data.msg || '请求失败',
        ErrorTypes.API,
        response.status,
        response.data
      )

      return {
        data: null,
        error,
      }
    }

    return {
      data: response.data,
      error: null,
    }
  } catch (err: any) {
    const errorType = getErrorType(err)
    const errorMessage = formatErrorMessage(err)
    const error = new ApiError(errorMessage, errorType, err.response?.status ?? null, err.response?.data ?? null)

    return {
      data: null,
      error,
    }
  }
}

export const request = <T = any>(config: AxiosRequestConfig) => handleRequest<T>(axios(config))

export const get = <T = any>(url: string, params?: unknown, config: AxiosRequestConfig = {}) =>
  request<T>({ url, method: 'get', params, ...config })
export const post = <T = any>(url: string, data?: unknown, config: AxiosRequestConfig = {}) =>
  request<T>({ url, method: 'post', data, ...config })
export const put = <T = any>(url: string, data?: unknown, config: AxiosRequestConfig = {}) =>
  request<T>({ url, method: 'put', data, ...config })
export const patch = <T = any>(url: string, data?: unknown, config: AxiosRequestConfig = {}) =>
  request<T>({ url, method: 'patch', data, ...config })
export const del = <T = any>(url: string, data?: unknown, config: AxiosRequestConfig = {}) =>
  request<T>({ url, method: 'delete', data, ...config })

export default request
