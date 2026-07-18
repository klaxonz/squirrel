import { get, post } from '@/shared/lib/request'

// FastAPI registers this router with a trailing slash. Calling the slashless
// URL makes the Vite proxy issue a 307 whose Location points at the backend
// origin, dropping the Electron renderer's proxy-origin auth cookie. Keep the
// request on the configured app origin instead of relying on that redirect.
const SYSTEM_CONFIG_PATH = '/api/system/config/'

export const getSystemConfig = async () => {
  return get<Record<string, unknown>>(SYSTEM_CONFIG_PATH)
}

export const saveSystemConfig = async (payload: Record<string, unknown> = {}) => {
  return post<Record<string, unknown>>(SYSTEM_CONFIG_PATH, payload)
}
