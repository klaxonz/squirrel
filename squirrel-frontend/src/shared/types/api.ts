// ponytail: this file previously aliased `RequestResult` as `ApiResult`. That
// result-tuple shape (`{ data, error }`) is gone — `get/post/...` now return `T`
// directly and throw `ApiError` on failure (vue-query error model). `ApiError`
// itself is re-exported here for any consumer that imported it via this path,
// though the canonical import is `@/shared/lib/request`.
export type { ApiError } from '@/shared/lib/request'
