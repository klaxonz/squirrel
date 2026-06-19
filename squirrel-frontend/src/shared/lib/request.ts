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

export type RequestResult<T = unknown> = {
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

const isApiEnvelope = (data: unknown): data is ApiEnvelope => {
  return !!data && typeof data === 'object' && typeof (data as ApiEnvelope).code === 'number'
}
const getErrorTypeByStatus = (status: number | null | undefined): ErrorType => {
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
const getErrorTypeByCode = (code: number, status: number | null | undefined): ErrorType => {
  const statusType = getErrorTypeByStatus(status)
  if (statusType !== ErrorTypes.API) return statusType

  switch (code) {
    case 401: return ErrorTypes.UNAUTHORIZED
    case 403: return ErrorTypes.FORBIDDEN
    case 404: return ErrorTypes.NOT_FOUND
    case 500: return ErrorTypes.SERVER_ERROR
    default: return ErrorTypes.API
  }
}
type AxiosErrorLike = { code?: string; response?: { status?: number; data?: unknown } } | null | undefined

const getErrorType = (error: unknown): ErrorType => {
  const err = error as AxiosErrorLike
  if (err?.code === 'ERR_CANCELED') {
    return ErrorTypes.CANCELED
  }

  if (!err?.response) {
    if (err?.code === 'ECONNABORTED') return ErrorTypes.TIMEOUT
    return ErrorTypes.NETWORK
  }

  return getErrorTypeByStatus(err.response.status)
}
const formatErrorMessage = (error: unknown) => {
  const err = error as { response?: { data?: { msg?: string } } } | null | undefined
  if (err?.response?.data?.msg) {
    return err.response.data.msg
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
export const handleRequest = async <T = unknown>(promise: Promise<AxiosResponse<unknown>>): Promise<RequestResult<T>> => {
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
        getErrorTypeByCode(response.data.code, response.status),
        response.status,
        response.data
      )

      return {
        data: null,
        error,
      }
    }

    return {
      data: response.data as T | null,
      error: null,
    }
  } catch (err: unknown) {
    const axiosErr = err as AxiosErrorLike
    const errorType = getErrorType(err)
    const errorMessage = formatErrorMessage(err)
    const error = new ApiError(errorMessage, errorType, axiosErr?.response?.status ?? null, axiosErr?.response?.data ?? null)

    return {
      data: null,
      error,
    }
  }
}

export const request = <T = unknown>(config: AxiosRequestConfig) => handleRequest<T>(axios(config))

export const get = <T = unknown>(url: string, params?: unknown, config: AxiosRequestConfig = {}) =>
  request<T>({ url, method: 'get', params, ...config })
export const post = <T = unknown>(url: string, data?: unknown, config: AxiosRequestConfig = {}) =>
  request<T>({ url, method: 'post', data, ...config })
export const put = <T = unknown>(url: string, data?: unknown, config: AxiosRequestConfig = {}) =>
  request<T>({ url, method: 'put', data, ...config })
export const patch = <T = unknown>(url: string, data?: unknown, config: AxiosRequestConfig = {}) =>
  request<T>({ url, method: 'patch', data, ...config })
export const del = <T = unknown>(url: string, data?: unknown, config: AxiosRequestConfig = {}) =>
  request<T>({ url, method: 'delete', data, ...config })

export default request
