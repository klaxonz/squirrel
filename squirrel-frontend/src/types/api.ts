export type ApiResult<T = any> = {
  data?: T | null
  error?: unknown | null
}
