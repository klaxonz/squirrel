import { ref, onMounted, onBeforeUnmount } from 'vue';
import { useProgressApi } from './useProgressApi';

/**
 * 订阅进度跟踪 Composable
 * 用于在订阅页面实时显示进度
 */
export function useSubscriptionProgress(subscriptionId, options = {}) {
  const {
    autoRefresh = true,
    refreshInterval = 3000, // 3秒刷新一次
    onProgressUpdate = null
  } = options;

  const { getLatestProgressBySubscription } = useProgressApi();
  
  const progress = ref(null);
  const loading = ref(false);
  const error = ref(null);
  
  let refreshTimer = null;

  /**
   * 加载最新进度
   */
  const loadProgress = async () => {
    if (!subscriptionId || !subscriptionId.value) return;
    
    try {
      loading.value = true;
      error.value = null;
      
      const result = await getLatestProgressBySubscription(subscriptionId.value);
      
      if (result.success) {
        const newProgress = result.data;
        
        // 只有在进度变化时才更新
        if (JSON.stringify(newProgress) !== JSON.stringify(progress.value)) {
          progress.value = newProgress;
          
          // 触发回调
          if (onProgressUpdate && typeof onProgressUpdate === 'function') {
            onProgressUpdate(newProgress);
          }
        }
      } else {
        error.value = result.error;
      }
    } catch (err) {
      console.error('加载进度失败:', err);
      error.value = err.message;
    } finally {
      loading.value = false;
    }
  };

  /**
   * 开始自动刷新
   */
  const startAutoRefresh = () => {
    if (refreshTimer) {
      clearInterval(refreshTimer);
    }
    
    if (autoRefresh) {
      refreshTimer = setInterval(() => {
        loadProgress();
      }, refreshInterval);
    }
  };

  /**
   * 停止自动刷新
   */
  const stopAutoRefresh = () => {
    if (refreshTimer) {
      clearInterval(refreshTimer);
      refreshTimer = null;
    }
  };

  /**
   * 检查是否正在处理中
   */
  const isProcessing = () => {
    if (!progress.value || !progress.value.event_type) return false;
    const eventType = progress.value.event_type;
    return eventType.includes('_start') || eventType.includes('_progress');
  };

  /**
   * 检查是否已完成
   */
  const isCompleted = () => {
    if (!progress.value || !progress.value.event_type) return false;
    return progress.value.event_type.includes('_complete');
  };

  /**
   * 检查是否有错误
   */
  const isError = () => {
    if (!progress.value || !progress.value.event_type) return false;
    return progress.value.event_type.includes('_error') || !!progress.value.error_message;
  };

  /**
   * 重置进度
   */
  const resetProgress = () => {
    progress.value = null;
    error.value = null;
  };

  // 初始化
  onMounted(() => {
    loadProgress();
    startAutoRefresh();
  });

  // 清理
  onBeforeUnmount(() => {
    stopAutoRefresh();
  });

  return {
    progress,
    loading,
    error,
    loadProgress,
    startAutoRefresh,
    stopAutoRefresh,
    isProcessing,
    isCompleted,
    isError,
    resetProgress
  };
}

