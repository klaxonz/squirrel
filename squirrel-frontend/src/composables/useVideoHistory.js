import axios from '../utils/axios';
import { ref, reactive } from 'vue';

export default function useVideoHistory() {
  // 本地缓存的播放历史
  const localHistory = reactive(new Map());

  // 待同步的历史记录队列
  const pendingUpdates = ref([]);

  // 同步状态
  const syncStatus = reactive({
    isOnline: navigator.onLine,
    lastSyncTime: null,
    failedAttempts: 0
  });

  // 发送播放进度报告（改进版）
  const sendReport = async (video_id, currentTime, options = {}) => {
    const {
      force = false,
      includeMetadata = false,
      retryOnFailure = true
    } = options;

    const reportData = {
      video_id,
      last_position: currentTime,
      timestamp: Date.now(),
      ...(includeMetadata && {
        user_agent: navigator.userAgent,
        viewport: {
          width: window.innerWidth,
          height: window.innerHeight
        },
        connection: navigator.connection ? {
          effectiveType: navigator.connection.effectiveType,
          downlink: navigator.connection.downlink
        } : null
      })
    };

    // 更新本地缓存
    updateLocalHistory(video_id, reportData);

    // 如果在线且不是强制模式，尝试立即发送
    if (syncStatus.isOnline || force) {
      try {
        await axios.post('/api/video-history/update', reportData);
        syncStatus.lastSyncTime = Date.now();
        syncStatus.failedAttempts = 0;

        // 移除已成功同步的记录
        removePendingUpdate(video_id);

        return true;
      } catch (error) {
        console.warn('Failed to sync video history:', error);
        syncStatus.failedAttempts++;

        if (retryOnFailure) {
          addToPendingUpdates(reportData);
        }

        return false;
      }
    } else {
      // 离线时添加到待同步队列
      addToPendingUpdates(reportData);
      return false;
    }
  };

  // 批量发送播放历史
  const sendBatchReport = async (reports) => {
    if (!syncStatus.isOnline || reports.length === 0) {
      return false;
    }

    try {
      await axios.post('/api/video-history/batch-update', {
        reports: reports
      });

      syncStatus.lastSyncTime = Date.now();
      syncStatus.failedAttempts = 0;

      // 清除已同步的记录
      reports.forEach(report => {
        removePendingUpdate(report.video_id);
      });

      return true;
    } catch (error) {
      console.error('Failed to batch sync video history:', error);
      syncStatus.failedAttempts++;
      return false;
    }
  };
  // 获取观看历史（分页，返回视频详情）
  const getWatchHistory = async (page = 1, filters = {}) => {
    try {
      const { nsfw, site, pageSize = 20 } = filters;
      const params = { page, page_size: pageSize };
      
      // 添加筛选参数
      if (nsfw && nsfw !== 'all') {
        params.nsfw = nsfw;
      }
      if (site && site !== 'all') {
        params.site = site;
      }
      
      const res = await axios.get('/api/video-history/list', { params });
      const resp = res?.data || {};
      if (resp.code !== 0) {
        throw new Error(resp.msg || '加载历史失败');
      }
      const payload = resp.data || {};
      const items = Array.isArray(payload.items) ? payload.items : [];
      return {
        items,
        total: payload.total ?? 0,
        page: payload.page ?? page,
        page_size: payload.page_size ?? pageSize
      };
    } catch (error) {
      throw new Error(error.message || '加载历史失败');
    }
  };

  // 清空观看历史（可选传入部分视频ID）
  const clearHistory = async (videoIds = null) => {
    try {
      const body = Array.isArray(videoIds) && videoIds.length ? videoIds : null;
      const res = await axios.post('/api/video-history/clear', body);
      const resp = res?.data || {};
      if (resp.code !== 0) {
        throw new Error(resp.msg || '清空历史失败');
      }
      return true;
    } catch (error) {
      throw new Error(error.message || '清空历史失败');
    }
  };


  // 获取本地播放历史
  const getLocalHistory = (video_id) => {
    return localHistory.get(video_id);
  };

  // 获取所有本地历史
  const getAllLocalHistory = () => {
    return Array.from(localHistory.values());
  };

  // 更新本地历史
  const updateLocalHistory = (video_id, data) => {
    const existing = localHistory.get(video_id);
    localHistory.set(video_id, {
      ...existing,
      ...data,
      lastUpdated: Date.now()
    });
  };

  // 添加到待同步队列
  const addToPendingUpdates = (reportData) => {
    const existingIndex = pendingUpdates.value.findIndex(
      update => update.video_id === reportData.video_id
    );

    if (existingIndex !== -1) {
      // 更新现有记录
      pendingUpdates.value[existingIndex] = reportData;
    } else {
      // 添加新记录
      pendingUpdates.value.push(reportData);
    }

    // 限制队列大小
    if (pendingUpdates.value.length > 100) {
      pendingUpdates.value = pendingUpdates.value.slice(-100);
    }
  };

  // 从待同步队列中移除
  const removePendingUpdate = (video_id) => {
    const index = pendingUpdates.value.findIndex(
      update => update.video_id === video_id
    );
    if (index !== -1) {
      pendingUpdates.value.splice(index, 1);
    }
  };

  // 同步所有待处理的更新
  const syncPendingUpdates = async () => {
    if (pendingUpdates.value.length === 0 || !syncStatus.isOnline) {
      return false;
    }

    // 分批同步，每批最多20条
    const batchSize = 20;
    const batches = [];

    for (let i = 0; i < pendingUpdates.value.length; i += batchSize) {
      batches.push(pendingUpdates.value.slice(i, i + batchSize));
    }

    let successCount = 0;
    for (const batch of batches) {
      const success = await sendBatchReport(batch);
      if (success) {
        successCount += batch.length;
      }
    }

    return successCount;
  };

  // 清理过期的本地历史
  const cleanupLocalHistory = (maxAge = 7 * 24 * 60 * 60 * 1000) => {
    const now = Date.now();
    const toDelete = [];

    for (const [video_id, data] of localHistory.entries()) {
      if (now - data.lastUpdated > maxAge) {
        toDelete.push(video_id);
      }
    }

    toDelete.forEach(video_id => {
      localHistory.delete(video_id);
    });

    return toDelete.length;
  };

  // 网络状态监听
  const setupNetworkListeners = () => {
    const handleOnline = () => {
      syncStatus.isOnline = true;
      console.debug('Network online, syncing pending updates...');
      syncPendingUpdates();
    };

    const handleOffline = () => {
      syncStatus.isOnline = false;
      console.debug('Network offline, updates will be queued');
    };

    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);

    // 返回清理函数
    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  };

  // 定期同步
  const startPeriodicSync = (interval = 30000) => {
    const syncInterval = setInterval(() => {
      if (syncStatus.isOnline && pendingUpdates.value.length > 0) {
        syncPendingUpdates();
      }

      // 定期清理过期历史
      if (Math.random() < 0.1) { // 10% 概率执行清理
        cleanupLocalHistory();
      }
    }, interval);

    return () => clearInterval(syncInterval);
  };

  return {
    // 基础功能
    sendReport,
    sendBatchReport,

    // 历史记录 API
    getWatchHistory,
    clearHistory,

    // 本地历史管理
    getLocalHistory,
    getAllLocalHistory,
    updateLocalHistory,

    // 同步管理
    syncPendingUpdates,
    cleanupLocalHistory,

    // 网络和定期同步
    setupNetworkListeners,
    startPeriodicSync,

    // 状态
    syncStatus,
    pendingUpdates,
    localHistory
  };
}