import type { AxiosRequestConfig } from 'axios'
import { ApiError, get, post } from '@/utils/request'

export const getSubscriptions = async (params: Record<string, unknown> = {}, config: AxiosRequestConfig = {}) => {
  return get<{ data?: unknown[]; items?: unknown[] }>('/api/subscription/list', params, config)
}

export const getSubscriptionOptions = async <T = unknown>() => {
  return get<T>('/api/subscription/options')
}

export const getSubscriptionDetail = async (subscriptionId: string | number) => {
  return get(`/api/subscription/detail/${subscriptionId}`)
}

export const unsubscribe = async (subscriptionId: string | number) => {
  return post<{ is_subscribed: boolean, subscription_id: number | null }>('/api/subscription/unsubscribe', {
    subscription_id: subscriptionId,
  })
}

export const subscribe = async (url: string) => {
  return post<{ is_subscribed: boolean, subscription_id: number | null }>('/api/subscription/subscribe', { url })
}

export const getSubscriptionStatus = async (url: string) => {
  return get<{ is_subscribed: boolean, subscription_id: number | null }>('/api/subscription/status', { url })
}

export const updateNsfwStatus = async (subscriptionId: string | number, isNsfw: boolean) => {
  const { data, error } = await post<{ success?: boolean }>('/api/subscription/toggle-nsfw', {
    subscription_id: subscriptionId,
    is_enable: isNsfw,
  })

  if (error) return { data: null, error }
  if (data?.success) return { data, error: null }

  return { data: null, error: new ApiError('更新失败', undefined, null, data) }
}

export const updateSpecialFollowStatus = async (subscriptionId: string | number, isSpecialFollowed: boolean) => {
  const { data, error } = await post<{ success?: boolean }>('/api/subscription/toggle-special-follow', {
    subscription_id: subscriptionId,
    is_enable: isSpecialFollowed,
  })

  if (error) return { data: null, error }
  if (data?.success) return { data, error: null }

  return { data: null, error: new ApiError('更新失败', undefined, null, data) }
}

export const triggerRefresh = async (subscriptionId: string | number, mode: string = 'incremental') => {
  const response = await post(`/api/subscription/${subscriptionId}/refresh`, null, {
    params: { mode },
  })
  if (!response.error) return response

  if (response.error.status === 429) {
    return {
      data: null,
      error: new ApiError('操作过于频繁，请稍后再试', response.error.type, response.error.status, response.error.data),
    }
  }

  if (response.error.status === 403) {
    return {
      data: null,
      error: new ApiError('没有权限执行此操作', response.error.type, response.error.status, response.error.data),
    }
  }

  return response
}

export const triggerDirectRefresh = async (subscriptionId: string | number, mode: string = 'incremental') => {
  const response = await post(`/api/subscription/${subscriptionId}/refresh/direct`, null, {
    params: { mode },
    timeout: 0,
  })
  if (!response.error) return response

  if (response.error.status === 403) {
    return {
      data: null,
      error: new ApiError('没有权限执行此操作', response.error.type, response.error.status, response.error.data),
    }
  }

  return response
}

export const getSupportedImportSites = async () => {
  const { data, error } = await get<{ sites?: string[] }>('/api/subscription/import/sites')
  return { data: data?.sites || [], error }
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
