export type ApiResult<T = unknown> = {
  data?: T | null
  error?: unknown | null
}
