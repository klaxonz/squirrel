import type { AxiosRequestConfig } from 'axios'
import axios from './axios'
import { ApiError, ErrorTypes, getErrorTypeByCode } from './apiError'

// Re-exported so existing `import { ApiError, ErrorTypes } from '@/shared/lib/request'`
// callsites keep working. The definitions live in apiError.ts to avoid a module
// cycle (axios.ts → request.ts → axios.ts).
export { ApiError, ErrorTypes }
export type { ErrorType } from './apiError'
export { isApiError, getErrorTypeByStatus, getErrorTypeByCode } from './apiError'

type ApiEnvelope<T = unknown> = {
  code: number
  msg?: string
  data?: T
}

const isApiEnvelope = (data: unknown): data is ApiEnvelope => {
  return !!data && typeof data === 'object' && typeof (data as ApiEnvelope).code === 'number'
}

/**
 * Unwrap the backend `{ code, msg, data }` envelope.
 *
 * The contract: HTTP success (2xx) with `code === 0` means the body's `data`
 * field is the payload; any other `code` is a business-level failure. We THROW
 * an `ApiError` on failure rather than returning `{ data, error }` — this is the
 * vue-query error model (useMutation/useQuery catch thrown errors). The old
 * `handleRequest` that swallowed exceptions into a Result tuple is gone; query's
 * `MutationCache.onError` is now the single global error-feedback channel.
 *
 * Transport failures (network/timeout/5xx) never reach here — the axios
 * response interceptor in `axios.ts` converts those into `ApiError` rejections
 * first. So by the time `response` resolves, only envelope logic remains.
 */
const unwrap = <T>(response: { data: unknown; status: number }): T => {
  const body = response.data
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
  return unwrap<T>({ data: response.data, status: response.status })
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
