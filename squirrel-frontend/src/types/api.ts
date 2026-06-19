// ponytail: re-export the real result shape from the request layer. Earlier
// this file declared a weaker `ApiResult<T>` ({ data?; error?: unknown }) and
// every call site `as ApiResult<T>`-cast the already-correct `RequestResult<T>`
// down to it — losing `error`'s `ApiError` type and forcing `as { message? }`
// re-narrows everywhere. `ApiResult` is kept as an alias so existing imports
// keep resolving while consumers are migrated off the cast pattern.
export type { RequestResult as ApiResult, ApiError } from '@/utils/request'
