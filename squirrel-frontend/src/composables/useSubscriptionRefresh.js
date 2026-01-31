import { reactive } from 'vue';
import { triggerRefresh as apiTriggerRefresh } from '../api/subscription'

const refreshStates = reactive(new Map());
const pollingTimers = reactive(new Map());
const subscriptionMeta = reactive(new Map());

export function useSubscriptionRefresh() {
  const getRefreshState = (subscriptionId) => {
    if (!refreshStates.has(subscriptionId)) {
      refreshStates.set(subscriptionId, {
        status: 'idle', // idle | queued | in_progress | completed | failed
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
      });
    }
    return refreshStates.get(subscriptionId);
  };
  
  const setSubscriptionMeta = (subscriptionId, meta) => {
    const prev = subscriptionMeta.get(subscriptionId) || {};
    subscriptionMeta.set(subscriptionId, { ...prev, ...meta });
  };

  const triggerRefresh = async (subscriptionId) => {
    const state = getRefreshState(subscriptionId);

    if (state.isRefreshing) {
      return false;
    }

    state.isRefreshing = true;

    const { data, error } = await apiTriggerRefresh(subscriptionId);

    if (!error && data) {

      state.status = data.status;
      state.requestId = data.requestId;
      state.isRefreshing = false;
      return true;
    } else {
      state.lastError = error;
      state.isRefreshing = false;
      return false;
    }
  };
  
  const retryRefresh = async (subscriptionId) => {
    const state = getRefreshState(subscriptionId);
    
    state.status = 'idle';
    state.lastError = null;
    state.isRefreshing = false;
    
    // 重新触发
    return await triggerRefresh(subscriptionId);
  };
  
  // 获取状态显示文本
  const getStatusText = (status, phase) => {
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
  };
  
  // 获取进度百分比
  const getProgressPercentage = (processed, total) => {
    if (!total || total === 0) return 0;
    return Math.round((processed / total) * 100);
  };
  
  // 清理所有轮询定时器
  const cleanup = () => {
    pollingTimers.forEach((timer) => { try { clearInterval(timer); } catch (_) {} });
    pollingTimers.clear();
  };
  
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
  };
}
