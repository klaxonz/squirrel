import { ref, reactive } from 'vue';
import { useSubscriptionApi } from './useSubscriptionApi';

export function useSubscriptionRefresh() {
  const { triggerRefresh: apiTriggerRefresh, getRefreshStatus: apiGetRefreshStatus } = useSubscriptionApi();
  
  // 存储每个订阅的刷新状态
  const refreshStates = reactive(new Map());
  
  // 轮询定时器
  const pollingTimers = reactive(new Map());
  
  // 获取订阅的刷新状态
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
  
  // 触发手动更新
  const triggerRefresh = async (subscriptionId) => {
    const state = getRefreshState(subscriptionId);

    // 防止重复触发
    if (state.isRefreshing) {
      return false;
    }

    state.isRefreshing = true;

    const result = await apiTriggerRefresh(subscriptionId);

    if (result.success) {
      const data = result.data;

      // 更新状态
      state.status = data.status;
      state.requestId = data.requestId;
      state.isRefreshing = data.inProgress || data.status === 'in_progress';

      if (data.status === 'queued' || data.status === 'in_progress') {
        startPolling(subscriptionId);
      }

      return true;
    } else {
      state.isRefreshing = false;
      return false;
    }
  };
  
  // 查询更新状态
  const fetchRefreshStatus = async (subscriptionId) => {
    const result = await apiGetRefreshStatus(subscriptionId);

    if (result.success) {
      const data = result.data;
      const state = getRefreshState(subscriptionId);

      // 更新状态
      Object.assign(state, {
        status: data.status,
        phase: data.phase,
        processed: data.processed || 0,
        total: data.total || 0,
        source: data.source,
        startedAt: data.startedAt,
        updatedAt: data.updatedAt,
        finishedAt: data.finishedAt,
        requestId: data.requestId,
        lastError: data.lastError,
        isRefreshing: data.status === 'queued' || data.status === 'in_progress'
      });

      // 如果更新完成或失败，停止轮询
      if (data.status === 'completed' || data.status === 'failed') {
        stopPolling(subscriptionId);
      }

      return data;
    }

    return null;
  };
  
  // 开始轮询
  const startPolling = (subscriptionId) => {
    // 清除现有定时器
    stopPolling(subscriptionId);
    
    const timer = setInterval(async () => {
      await fetchRefreshStatus(subscriptionId);
    }, 3000); // 每3秒轮询一次
    
    pollingTimers.set(subscriptionId, timer);
  };
  
  // 停止轮询
  const stopPolling = (subscriptionId) => {
    const timer = pollingTimers.get(subscriptionId);
    if (timer) {
      clearInterval(timer);
      pollingTimers.delete(subscriptionId);
    }
  };
  
  // 重试更新
  const retryRefresh = async (subscriptionId) => {
    const state = getRefreshState(subscriptionId);
    
    // 重置状态
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
        case 'init': return '初始化';
        case 'fetching_feed': return '获取订阅源';
        case 'calculating_delta': return '计算差异';
        case 'extracting': return '解析视频';
        case 'finalizing': return '完成中';
        default: return '更新中';
      }
    }
    if (status === 'completed') return '已完成';
    if (status === 'failed') return '更新失败';
    return '';
  };
  
  // 获取进度百分比
  const getProgressPercentage = (processed, total) => {
    if (!total || total === 0) return 0;
    return Math.round((processed / total) * 100);
  };
  
  // 清理所有轮询定时器
  const cleanup = () => {
    pollingTimers.forEach((timer) => {
      clearInterval(timer);
    });
    pollingTimers.clear();
  };
  
  return {
    refreshStates,
    getRefreshState,
    triggerRefresh,
    fetchRefreshStatus,
    retryRefresh,
    getStatusText,
    getProgressPercentage,
    cleanup
  };
}
