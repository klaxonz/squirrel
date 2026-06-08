import axios from 'axios'
import type { AxiosError } from 'axios'
import { getServerUrl } from './serverConfig'
import { logoutAndRedirect } from './auth'

const generateTraceId = () => {
  const hex = '0123456789abcdef'
  let id = ''
  for (let i = 0; i < 32; i++) {
    id += hex[Math.floor(Math.random() * 16)]
  }
  return id
}

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

instance.interceptors.response.use(
  (response) => {
    return response
  },
  (error: AxiosError<any>) => {
    if (error.response?.data?.msg) {
      error.message = error.response.data.msg
    }

    if (error.response?.status === 401) {
      void logoutAndRedirect()
    }
    return Promise.reject(error)
  }
)

export const invalidateBaseUrlCache = () => {}

export default instance
