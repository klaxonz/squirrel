import type { AxiosRequestConfig } from 'axios'
import axios from './axios'
import { ApiError, ErrorTypes, getErrorTypeByCode } from './apiError'

// Re-exported so existing `import { ApiError, ErrorTypes } from '@/shared/lib/request'`
// callsites keep working. The definitions live in apiError.ts to avoid a module
// cycle (axios.ts → request.ts → axios.ts).
export { ApiError, ErrorTypes }
export type { ErrorType } from './apiError'
export { isApiError, getErrorTypeByStatus, getErrorTypeByCode } from './apiError'

/** Backend's JSON response envelope. JSON requests use this shape by default. */
export type ApiEnvelope<T = unknown> = {
  code: number
  msg?: string
  data?: T
}

const isApiEnvelope = (data: unknown): data is ApiEnvelope => {
  return !!data && typeof data === 'object' && typeof (data as ApiEnvelope).code === 'number'
}

/**
 * Resolve the response according to its declared response mode.
 *
 * JSON requests expect the backend `{ code, msg, data }` envelope: `code === 0`
 * returns `data`, and every other code throws an `ApiError`. Non-JSON requests
 * (for example `responseType: 'text'`) are raw responses and bypass envelope
 * detection entirely, even when the raw value happens to contain `code`.
 *
 * Transport failures (network/timeout/5xx) never reach here — the axios
 * response interceptor in `axios.ts` converts those into `ApiError` rejections
 * first.
 */
const unwrap = <T>(response: { data: unknown; status: number; responseType?: AxiosRequestConfig['responseType'] }): T => {
  const body = response.data
  if (response.responseType && response.responseType !== 'json') return body as T
  if (isApiEnvelope(body)) {
    if (body.code === 0) {
      return (body.data ?? null) as T
    }
    throw new ApiError(
      body.msg || '请求失败',
      getErrorTypeByCode(body.code, response.status),
      response.status,
      body,
    )
  }
  return body as T
}

export const request = async <T = unknown>(config: AxiosRequestConfig): Promise<T> => {
  const response = await axios.request<T>(config)
  return unwrap<T>({ data: response.data, status: response.status, responseType: config.responseType })
}

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
