import { reactive } from 'vue';
import { useSubscriptionApi } from './useSubscriptionApi';

// 单例状态：多个组件共享
const refreshStates = reactive(new Map());
const pollingTimers = reactive(new Map());
let globalPollingTimer = null; // 单一全局轮询，降低请求量
const subscriptionMeta = reactive(new Map()); // { id: { name, avatar } }

export function useSubscriptionRefresh() {
  const { triggerRefresh: apiTriggerRefresh, getRefreshStatus: apiGetRefreshStatus, getActiveRefreshTasks } = useSubscriptionApi();
  
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
  
  // 记录订阅的展示信息（可选）
  const setSubscriptionMeta = (subscriptionId, meta) => {
    const prev = subscriptionMeta.get(subscriptionId) || {};
    subscriptionMeta.set(subscriptionId, { ...prev, ...meta });
  };

  // 本地不做持久化，所有状态以服务端为准

  // 启动全局轮询：统一从服务端批量获取活跃任务，避免每个订阅独立轮询
  const startGlobalPolling = () => {
    if (globalPollingTimer) return;
    globalPollingTimer = setInterval(async () => {
      try {
        const result = await getActiveRefreshTasks();
        if (!result.success) return;
        const items = result.data || [];
        const activeIds = new Set(items.map(i => i.subscriptionId));

        for (const item of items) {
          const state = getRefreshState(item.subscriptionId);
          state.status = item.status;
          state.phase = item.phase;
          state.processed = item.processed || 0;
          state.total = item.total || 0;
          state.requestId = item.requestId || null;
          state.startedAt = item.startedAt || null;
          state.updatedAt = item.updatedAt || null;
          state.isRefreshing = item.status === 'queued' || item.status === 'in_progress';
          if (item.meta) subscriptionMeta.set(item.subscriptionId, item.meta);
        }

        // 不在活跃列表但之前标记为刷新中的任务，置为静默
        refreshStates.forEach((state, id) => {
          if (!activeIds.has(id) && (state.isRefreshing || state.status === 'queued' || state.status === 'in_progress')) {
            state.isRefreshing = false;
          }
        });

        // 没有活跃任务自动停止轮询
        if (items.length === 0) {
          stopGlobalPolling();
        }
      } catch (_) {}
    }, 3000);
  };

  const stopGlobalPolling = () => {
    if (globalPollingTimer) {
      clearInterval(globalPollingTimer);
      globalPollingTimer = null;
    }
  };

  // 从服务端恢复进行中的任务
  const rehydrateFromServer = async () => {
    try {
      const result = await getActiveRefreshTasks();
      if (!result.success) return;
      for (const item of result.data) {
        const state = getRefreshState(item.subscriptionId);
        state.status = item.status;
        state.phase = item.phase;
        state.processed = item.processed || 0;
        state.total = item.total || 0;
        state.requestId = item.requestId || null;
        state.startedAt = item.startedAt || null;
        state.updatedAt = item.updatedAt || null;
        state.isRefreshing = item.status === 'queued' || item.status === 'in_progress';
        if (item.meta) subscriptionMeta.set(item.subscriptionId, item.meta);
        if (state.isRefreshing) startPolling(item.subscriptionId);
      }
      persistActiveTasks();
    } catch (_) {}
  }
  
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
  const startPolling = (_subscriptionId) => {
    // 改为全局轮询，避免多路请求
    startGlobalPolling();
  };
  
  // 停止轮询
  const stopPolling = (_subscriptionId) => {
    // 当没有活跃任务时停止全局轮询
    const hasActive = Array.from(refreshStates.values()).some(s => s.isRefreshing || s.status === 'queued' || s.status === 'in_progress');
    if (!hasActive) {
      stopGlobalPolling();
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
        case 'init': return '准备中';
        case 'fetching_feed': return '检查新内容';
        case 'calculating_delta': return '分析更新';
        case 'extracting': return '处理新视频';
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
    stopGlobalPolling();
  };
  
  return {
    refreshStates,
    subscriptionMeta,
    getRefreshState,
    triggerRefresh,
    fetchRefreshStatus,
    retryRefresh,
    getStatusText,
    getProgressPercentage,
    cleanup,
    setSubscriptionMeta,
    rehydrateFromServer
    ,startGlobalPolling
  };
}
