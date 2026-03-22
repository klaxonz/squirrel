import { ApiError, get, post } from '@/utils/request'

export const getSubscriptions = async (params: Record<string, unknown> = {}) => {
  return get('/api/subscription/list', params)
}

export const getSubscriptionOptions = async <T = any>() => {
  return get<T>('/api/subscription/options')
}

export const getSubscriptionDetail = async (subscriptionId: string | number) => {
  return get(`/api/subscription/detail/${subscriptionId}`)
}

export const unsubscribe = async (subscriptionId: string | number) => {
  return post('/api/subscription/unsubscribe', {
    subscription_id: subscriptionId,
  })
}

export const subscribe = async (url: string) => {
  return post('/api/subscription/subscribe', { url })
}

export const updateNsfwStatus = async (subscriptionId: string | number, isNsfw: boolean) => {
  const { data, error } = await post('/api/subscription/toggle-nsfw', {
    subscription_id: subscriptionId,
    is_enable: isNsfw,
  })

  if (error) return { data: null, error }
  if (data?.success) return { data, error: null }

  return { data: null, error: new ApiError('更新失败', undefined, null, data) }
}

export const triggerRefresh = async (subscriptionId: string | number, mode: string = 'incremental') => {
  const result = await post(`/api/subscription/${subscriptionId}/refresh`, null, {
    params: { mode },
  })
  if (!result.error) return result

  if (result.error.status === 429) {
    return {
      data: null,
      error: new ApiError('操作过于频繁，请稍后再试', result.error.type, result.error.status, result.error.data),
    }
  }

  if (result.error.status === 403) {
    return {
      data: null,
      error: new ApiError('没有权限执行此操作', result.error.type, result.error.status, result.error.data),
    }
  }

  return result
}

export const getSupportedImportSites = async () => {
  const { data, error } = await get('/api/subscription/import/sites')
  return { data: data?.sites || [], error }
}

export const previewImportSubscriptions = async (site: string) => {
  return get(`/api/subscription/import/${site}/preview`)
}

export const importSubscriptions = async (site: string, subscriptionUrls: string[] | null = null) => {
  const payload = subscriptionUrls ? { subscription_urls: subscriptionUrls } : {}
  return post(`/api/subscription/import/${site}`, payload)
}
