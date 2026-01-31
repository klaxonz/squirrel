import { reactive } from 'vue'
import { triggerRefresh as apiTriggerRefresh } from '@/api'

type SubscriptionId = string | number
type RefreshStatus = 'idle' | 'queued' | 'in_progress' | 'completed' | 'failed'

type RefreshState = {
  status: RefreshStatus
  phase: string | null
  processed: number
  total: number
  source: string | null
  startedAt: number | null
  updatedAt: number | null
  finishedAt: number | null
  requestId: string | null
  lastError: unknown | null
  isRefreshing: boolean
}

type RefreshMeta = Record<string, unknown>
type ApiResult<T> = { data?: T | null; error?: unknown | null }
type TriggerRefreshResponse = { status: RefreshStatus; requestId: string | null }

const refreshStates = reactive(new Map<SubscriptionId, RefreshState>()) as Map<SubscriptionId, RefreshState>
const pollingTimers = reactive(new Map<SubscriptionId, number>()) as Map<SubscriptionId, number>
const subscriptionMeta = reactive(new Map<SubscriptionId, RefreshMeta>()) as Map<SubscriptionId, RefreshMeta>

export function useSubscriptionRefresh() {
  const getRefreshState = (subscriptionId: SubscriptionId) => {
    if (!refreshStates.has(subscriptionId)) {
      refreshStates.set(subscriptionId, {
        status: 'idle',
        phase: null,
        processed: 0,
        total: 0,
        source: null,
        startedAt: null,
        updatedAt: null,
        finishedAt: null,
        requestId: null,
        lastError: null,
        isRefreshing: false
      })
    }
    return refreshStates.get(subscriptionId)!
  }
  
  const setSubscriptionMeta = (subscriptionId: SubscriptionId, meta: RefreshMeta) => {
    const prev = subscriptionMeta.get(subscriptionId) || {}
    subscriptionMeta.set(subscriptionId, { ...prev, ...meta })
  }

  const triggerRefresh = async (subscriptionId: SubscriptionId) => {
    const state = getRefreshState(subscriptionId)

    if (state.isRefreshing) {
      return false
    }

    state.isRefreshing = true

    const { data, error } = (await apiTriggerRefresh(subscriptionId)) as ApiResult<TriggerRefreshResponse>

    if (!error && data) {

      state.status = data.status
      state.requestId = data.requestId
      state.isRefreshing = false
      return true
    } else {
      state.lastError = error || null
      state.isRefreshing = false
      return false
    }
  }
  
  const retryRefresh = async (subscriptionId: SubscriptionId) => {
    const state = getRefreshState(subscriptionId)
    
    state.status = 'idle'
    state.lastError = null
    state.isRefreshing = false
    
    return await triggerRefresh(subscriptionId)
  }
  
  const getStatusText = (status: RefreshStatus, phase: string | null) => {
    if (status === 'queued') return '排队中';
    if (status === 'in_progress') {
      switch (phase) {
        case 'init': return '准备中';
        case 'fetching_feed': return '检查新内容';
        case 'calculating_delta': return '分析更新';
        case 'extracting': return '解析中';
        case 'finalizing': return '即将完成';
        default: return '同步中';
      }
    }
    if (status === 'completed') return '已完成';
    if (status === 'failed') return '同步失败';
    return '';
  }
  
  const getProgressPercentage = (processed: number, total: number) => {
    if (!total || total === 0) return 0
    return Math.round((processed / total) * 100)
  }
  
  const cleanup = () => {
    pollingTimers.forEach((timer) => {
      try {
        clearInterval(timer)
      } catch (_) {}
    })
    pollingTimers.clear()
  }
  
  return {
    refreshStates,
    subscriptionMeta,
    getRefreshState,
    triggerRefresh,
    retryRefresh,
    getStatusText,
    getProgressPercentage,
    cleanup,
    setSubscriptionMeta
  }
}
