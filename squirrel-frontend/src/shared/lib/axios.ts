import axios from 'axios'
import type { AxiosError } from 'axios'
import { getServerUrl } from './serverConfig'
import { logoutAndRedirect } from './auth'
import { ApiError, formatTransportErrorMessage, getTransportErrorType } from './apiError'

const generateTraceId = () => crypto.randomUUID().replace(/-/g, '')

const instance = axios.create({
  timeout: 60000,
  withCredentials: true,
  headers: {
    'Content-Type': 'application/json',
  },
})

instance.interceptors.request.use((config) => {
  const base = getServerUrl()
  if (base && !config.url?.startsWith('http')) {
    config.baseURL = base
  }
  config.headers.set('X-Trace-Id', generateTraceId())
  return config
})

// ponytail: transport-level errors (network/timeout/5xx) are converted here into
// `ApiError` rejections so the whole app sees one error type. Envelope business
// errors (HTTP 200, code !== 0) are thrown later inside request.ts's `unwrap`.
// The 401 → logout side-effect stays at this transport layer (it's orthogonal to
// vue-query: the request fails, the app logs out, query's onError may still toast).
// Error classification + message formatting live in apiError.ts (single source).
instance.interceptors.response.use(
  (response) => response,
  (error: AxiosError<unknown>) => {
    if (error.response?.status === 401) {
      void logoutAndRedirect()
    }
    const status = error.response?.status ?? null
    return Promise.reject(new ApiError(formatTransportErrorMessage(error), getTransportErrorType(error), status, error.response?.data ?? null))
  }
)

export default instance

