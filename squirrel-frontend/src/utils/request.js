import axios from './axios'

export default function request(config) {
  return axios(config)
}

/**
 * 统一的错误类型枚举
 */
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

/**
 * 自定义错误类
 */
export class ApiError extends Error {
  constructor(message, type = ErrorTypes.UNKNOWN, status = null, data = null) {
    super(message)
    this.name = 'ApiError'
    this.type = type
    this.status = status
    this.data = data
  }
}

/**
 * 获取错误类型
 */
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

/**
 * 格式化错误消息
 */
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

/**
 * 处理API响应
 */
export const handleRequest = async (promise) => {
  try {
    const response = await promise

    // API 成功响应
    if (response.data && typeof response.data.code === 'number') {
      if (response.data.code === 0) {
        return {
          data: response.data.data,
          error: null,
        }
      }

      // API 业务错误
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

    // 兼容旧的响应格式
    return {
      data: response.data,
      error: null,
    }
  } catch (err) {
    // 网络或其他错误
    const errorType = getErrorType(err)
    const errorMessage = formatErrorMessage(err)
    const error = new ApiError(errorMessage, errorType, err.response?.status, err.response?.data)

    return {
      data: null,
      error,
    }
  }
}

export const get = (url, params) => handleRequest(axios.get(url, { params }))
export const post = (url, data) => handleRequest(axios.post(url, data))
export const put = (url, data) => handleRequest(axios.put(url, data))
export const del = (url, data) => handleRequest(axios.delete(url, { data })) 
