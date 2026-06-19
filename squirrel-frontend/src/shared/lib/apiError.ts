/**
 * Pure API error types — no axios/request imports, so both `axios.ts`
 * (transport interceptor) and `request.ts` (envelope unwrap) can import from
 * here without creating a module cycle (axios.ts → request.ts → axios.ts).
 */

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

/**
 * Type guard — used across the app to distinguish `ApiError` (from the request
 * layer) from other thrown values (e.g. desktop-bridge `Error`s).
 */
export const isApiError = (error: unknown): error is ApiError => error instanceof ApiError

type AxiosErrorLike = { code?: string; response?: { status?: number; data?: unknown } } | null | undefined

/**
 * Map an HTTP status to its semantic `ErrorType`. Shared by the transport
 * interceptor (axios.ts) and the envelope unwrap (request.ts) so there's one
 * place that knows status → type. Previously duplicated across both files.
 */
export const getErrorTypeByStatus = (status: number | null | undefined): ErrorType => {
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

/**
 * Map a transport-level error (axios rejection / network failure) to its
 * `ErrorType`. Used by the axios response interceptor.
 */
export const getTransportErrorType = (error: unknown): ErrorType => {
  const err = error as AxiosErrorLike
  if (err?.code === 'ERR_CANCELED') return ErrorTypes.CANCELED
  if (!err?.response) {
    if (err?.code === 'ECONNABORTED') return ErrorTypes.TIMEOUT
    return ErrorTypes.NETWORK
  }
  return getErrorTypeByStatus(err.response.status)
}

/**
 * Map a backend envelope `{ code }` (business-level failure on an HTTP-200
 * response) to its `ErrorType`. Falls back to the HTTP status-derived type when
 * the code isn't a known business code. Used by the envelope unwrap in request.ts.
 */
export const getErrorTypeByCode = (code: number, status: number | null | undefined): ErrorType => {
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

/**
 * Build a user-facing message from a transport error. Prefers the server's
 * `msg`, then falls back to a type-specific localized string. Used by the axios
 * interceptor so every transport failure carries a readable message.
 */
export const formatTransportErrorMessage = (error: unknown): string => {
  const err = error as { response?: { data?: { msg?: string } } } | null | undefined
  if (err?.response?.data?.msg) return err.response.data.msg
  switch (getTransportErrorType(error)) {
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

