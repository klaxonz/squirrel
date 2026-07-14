import type { AxiosRequestConfig } from 'axios'
import { ApiError, ErrorTypes, get, post } from '@/shared/lib/request'
import type {
  SubscriptionListResponse,
  SubscriptionDetail,
  SubscriptionOption,
  SubscriptionToggleResult,
} from '@/features/video/types/subscription'

export const getSubscriptions = async (params: Record<string, unknown> = {}, config: AxiosRequestConfig = {}) => {
  return get<SubscriptionListResponse>('/api/subscription/list', params, config)
}

export const getSubscriptionOptions = async () => {
  return get<{ data: SubscriptionOption[] }>('/api/subscription/options')
}

export const getSubscriptionDetail = async (subscriptionId: string | number) => {
  return get<SubscriptionDetail>(`/api/subscription/detail/${subscriptionId}`)
}

export const unsubscribe = async (subscriptionId: string | number) => {
  return post<SubscriptionToggleResult>('/api/subscription/unsubscribe', {
    subscription_id: subscriptionId,
  })
}

export const subscribe = async (url: string) => {
  return post<SubscriptionToggleResult>('/api/subscription/subscribe', { url })
}

export const getSubscriptionStatus = async (url: string) => {
  return get<SubscriptionToggleResult>('/api/subscription/status', { url })
}

export const updateNsfwStatus = async (subscriptionId: string | number, isNsfw: boolean) => {
  const data = await post<{ success?: boolean }>('/api/subscription/toggle-nsfw', {
    subscription_id: subscriptionId,
    is_enable: isNsfw,
  })
  if (!data?.success) {
    throw new ApiError('更新失败', ErrorTypes.UNKNOWN, null, data)
  }
  return data
}

export const updateSpecialFollowStatus = async (subscriptionId: string | number, isSpecialFollowed: boolean) => {
  const data = await post<{ success?: boolean }>('/api/subscription/toggle-special-follow', {
    subscription_id: subscriptionId,
    is_enable: isSpecialFollowed,
  })
  if (!data?.success) {
    throw new ApiError('更新失败', ErrorTypes.UNKNOWN, null, data)
  }
  return data
}

// ponytail: transport/envelope errors are thrown by post(); we catch here only
// to rewrite the status-specific user-facing message (429/403) and re-throw,
// so the global MutationCache.onError toasts the friendlier wording.
export const triggerRefresh = async (subscriptionId: string | number, mode: string = 'incremental') => {
  try {
    return await post(`/api/subscription/${subscriptionId}/refresh`, null, { params: { mode } })
  } catch (e) {
    if (e instanceof ApiError && e.status === 429) {
      throw new ApiError('操作过于频繁，请稍后再试', e.type, e.status, e.data)
    }
    throw e
  }
}

export const triggerDirectRefresh = async (subscriptionId: string | number, mode: string = 'incremental') => {
  try {
    return await post(`/api/subscription/${subscriptionId}/refresh/direct`, null, {
      params: { mode },
      timeout: 0,
    })
  } catch (e) {
    if (e instanceof ApiError && e.status === 403) {
      throw new ApiError('没有权限执行此操作', e.type, e.status, e.data)
    }
    throw e
  }
}

export const getSupportedImportSites = async () => {
  const data = await get<{ sites?: string[] }>('/api/subscription/import/sites')
  return data?.sites || []
}

export const previewImportSubscriptions = async (
  site: string,
  options: { cursorPayload?: Record<string, unknown> | null, limit?: number } = {},
) => {
  const params: Record<string, unknown> = {}
  if (options.cursorPayload) {
    params.cursor = JSON.stringify(options.cursorPayload)
  }
  if (typeof options.limit === 'number') {
    params.limit = options.limit
  }
  return get(`/api/subscription/import/${site}/preview`, params)
}

export const importSubscriptions = async (site: string, subscriptionUrls: string[] | null = null) => {
  const payload = subscriptionUrls ? { subscription_urls: subscriptionUrls } : {}
  return post(`/api/subscription/import/${site}`, payload)
}
