import { ApiError, get, post } from '../utils/request'

export function useSubscriptionApi() {
  // 获取订阅列表
  const getSubscriptions = async (params = {}) => {
    return get('/api/subscription/list', params)
  };

  // 获取订阅详情
  const getSubscriptionDetail = async (subscriptionId) => {
    return get(`/api/subscription/detail/${subscriptionId}`)
  };

  // 取消订阅
  const unsubscribe = async (subscriptionId) => {
    return post('/api/subscription/unsubscribe', {
      subscription_id: subscriptionId,
    })
  };

  // 更新NSFW状态
  const updateNsfwStatus = async (subscriptionId, isNsfw) => {
    const { data, error } = await post('/api/subscription/toggle-nsfw', {
      subscription_id: subscriptionId,
      is_enable: isNsfw,
    })

    if (error) return { data: null, error }
    if (data?.success) return { data, error: null }

    return { data: null, error: new ApiError('更新失败', undefined, null, data) }
  };

  // 触发手动更新
  const triggerRefresh = async (subscriptionId) => {
    const result = await post(`/api/subscription/${subscriptionId}/refresh`, null)
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
  };

  // 获取支持导入的站点列表
  const getSupportedImportSites = async () => {
    const { data, error } = await get('/api/subscription/import/sites')
    return {
      data: data?.sites || [],
      error,
    }
  };

  // 预览订阅列表
  const previewImportSubscriptions = async (site) => {
    return get(`/api/subscription/import/${site}/preview`)
  };

  // 执行导入
  const importSubscriptions = async (site, subscriptionUrls = null) => {
    const payload = subscriptionUrls ? { subscription_urls: subscriptionUrls } : {}
    return post(`/api/subscription/import/${site}`, payload)
  };

  return {
    getSubscriptions,
    getSubscriptionDetail,
    unsubscribe,
    updateNsfwStatus,
    triggerRefresh,
    getSupportedImportSites,
    previewImportSubscriptions,
    importSubscriptions
  };
}
