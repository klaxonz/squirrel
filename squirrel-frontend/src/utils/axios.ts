import axios from 'axios'
import type { AxiosError } from 'axios'
import { logoutAndRedirect } from './auth'

const instance = axios.create({
  timeout: 60000,
  withCredentials: true,
  headers: {
    'Content-Type': 'application/json',
  },
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

export default instance
