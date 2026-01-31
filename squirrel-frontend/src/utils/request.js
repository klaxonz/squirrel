import axios from './axios'
export const ErrorTypes = {
  NETWORK: 'NETWORK',
  API: 'API',
  TIMEOUT: 'TIMEOUT',
  UNAUTHORIZED: 'UNAUTHORIZED',
  FORBIDDEN: 'FORBIDDEN',
  NOT_FOUND: 'NOT_FOUND',
  SERVER_ERROR: 'SERVER_ERROR',
  UNKNOWN: 'UNKNOWN',
}
export class ApiError extends Error {
  constructor(message, type = ErrorTypes.UNKNOWN, status = null, data = null) {
    super(message)
    this.name = 'ApiError'
    this.type = type
    this.status = status
    this.data = data
  }
}

const isApiEnvelope = (data) => {
  return !!data && typeof data.code === 'number'
}
const getErrorType = (error) => {
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
const formatErrorMessage = (error) => {
  if (error.response?.data?.msg) {
    return error.response.data.msg
  }

  switch (getErrorType(error)) {
    case ErrorTypes.NETWORK: return '网络连接失败，请检查网络设置'
    case ErrorTypes.TIMEOUT: return '请求超时，请稍后重试'
    case ErrorTypes.UNAUTHORIZED: return '登录已过期，请重新登录'
    case ErrorTypes.FORBIDDEN: return '权限不足'
    case ErrorTypes.NOT_FOUND: return '请求的资源不存在'
    case ErrorTypes.SERVER_ERROR: return '服务器错误，请稍后重试'
    default: return '请求失败，请稍后重试'
  }
}
export const handleRequest = async (promise) => {
  try {
    const response = await promise

    if (isApiEnvelope(response.data)) {
      if (response.data.code === 0) {
        return {
          data: response.data.data,
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
  } catch (err) {
    const errorType = getErrorType(err)
    const errorMessage = formatErrorMessage(err)
    const error = new ApiError(errorMessage, errorType, err.response?.status, err.response?.data)

    return {
      data: null,
      error,
    }
  }
}

export const request = (config) => handleRequest(axios(config))

export const get = (url, params, config = {}) => request({ url, method: 'get', params, ...config })
export const post = (url, data, config = {}) => request({ url, method: 'post', data, ...config })
export const put = (url, data, config = {}) => request({ url, method: 'put', data, ...config })
export const del = (url, data, config = {}) => request({ url, method: 'delete', data, ...config })

export default request
