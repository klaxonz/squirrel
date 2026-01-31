import axios from 'axios'
import type { AxiosError, InternalAxiosRequestConfig } from 'axios'
import { logoutAndRedirect } from './auth'

const instance = axios.create({
  timeout: 60000,
  headers: {
    'Content-Type': 'application/json',
  },
})

instance.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    const token = localStorage.getItem('token')
    if (token) {
      if (!config.headers) config.headers = {}
      ;(config.headers as any).Authorization = `Bearer ${token}`
    }
    return config
  },
  (error: AxiosError) => {
    return Promise.reject(error)
  }
)

instance.interceptors.response.use(
  (response) => {
    return response
  },
  (error: AxiosError<any>) => {
    if (error.response?.data?.msg) {
      error.message = error.response.data.msg
    }

    if (error.response?.status === 401) {
      logoutAndRedirect()
    }
    return Promise.reject(error)
  }
)

export default instance
