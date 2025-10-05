import axios from '../utils/axios';
import useCustomToast from './useToast';

export function useSubscriptionApi() {
  const { displayToast, confirm } = useCustomToast();

  // 获取订阅列表
  const getSubscriptions = async (params = {}) => {
    try {
      const response = await axios.get('/api/subscription/list', { params });
      if (response.data.code === 0) {
        return {
          success: true,
          data: response.data.data
        };
      } else {
        throw new Error(response.data.msg || '获取订阅列表失败');
      }
    } catch (error) {
      console.error('获取订阅列表失败:', error);
      return {
        success: false,
        error: error.message || '获取订阅列表失败'
      };
    }
  };

  // 获取订阅详情
  const getSubscriptionDetail = async (subscriptionId) => {
    try {
      const response = await axios.get(`/api/subscription/detail/${subscriptionId}`);
      if (response.data.code === 0) {
        return { success: true, data: response.data.data };
      } else {
        throw new Error(response.data.msg || '获取订阅详情失败');
      }
    } catch (error) {
      console.error('获取订阅详情失败:', error);
      return { success: false, error: error.message || '获取订阅详情失败' };
    }
  };

  // 取消订阅
  const unsubscribe = async (subscriptionId) => {
    const confirmed = await confirm('确定要取消订阅这个频道吗？这将删除所有相关的视频记录。');
    
    if (!confirmed) {
      return { success: false, cancelled: true };
    }

    try {
      const response = await axios.post('/api/subscription/unsubscribe', {
        subscription_id: subscriptionId
      });
      
      if (response.data.code === 0) {
        displayToast('取消订阅成功');
        return { success: true };
      } else {
        throw new Error(response.data.msg || '取消订阅失败');
      }
    } catch (error) {
      console.error('取消订阅失败:', error);
      const errorMessage = error.message || '取消订阅失败';
      displayToast(errorMessage, { type: 'error' });
      return {
        success: false,
        error: errorMessage
      };
    }
  };

  // 更新NSFW状态
  const updateNsfwStatus = async (subscriptionId, isNsfw) => {
    try {
      const response = await axios.post('/api/subscription/toggle-nsfw', {
        subscription_id: subscriptionId,
        is_enable: isNsfw
      });
      
      if (response.data.success) {
        return { success: true };
      } else {
        throw new Error('更新失败');
      }
    } catch (error) {
      console.error('更新NSFW状态失败:', error);
      return {
        success: false,
        error: error.message || '更新失败'
      };
    }
  };

  // 触发手动更新
  const triggerRefresh = async (subscriptionId) => {
    try {
      const response = await axios.post(`/api/subscription/${subscriptionId}/refresh`);
      
      if (response.data.code === 0) {
        const data = response.data.data;
        return {
          success: true,
          data: data
        };
      } else {
        throw new Error(response.data.msg || '触发更新失败');
      }
    } catch (error) {
      console.error('触发更新失败:', error);
      
      let errorMessage = '触发更新失败';
      if (error.response?.status === 429) {
        errorMessage = '操作过于频繁，请稍后再试';
      } else if (error.response?.status === 403) {
        errorMessage = '没有权限执行此操作';
      } else if (error.message) {
        errorMessage = error.message;
      }
      
      displayToast(errorMessage, { type: 'error' });
      return {
        success: false,
        error: errorMessage
      };
    }
  };

  // 查询更新状态
  const getRefreshStatus = async (subscriptionId) => {
    try {
      const response = await axios.get(`/api/subscription/${subscriptionId}/refresh/status`);
      
      if (response.data.code === 0) {
        return {
          success: true,
          data: response.data.data
        };
      } else {
        throw new Error(response.data.msg || '获取状态失败');
      }
    } catch (error) {
      console.error('获取更新状态失败:', error);
      return {
        success: false,
        error: error.message || '获取状态失败'
      };
    }
  };

  // 获取当前用户的所有进行中刷新任务（用于页面刷新后的恢复）
  const getActiveRefreshTasks = async () => {
    try {
      const response = await axios.get(`/api/subscription/refresh/active`);
      if (response.data.code === 0) {
        return { success: true, data: response.data.data.items || [] };
      }
      throw new Error(response.data.msg || '获取进行中任务失败');
    } catch (error) {
      console.error('获取进行中任务失败:', error);
      return { success: false, error: error.message || '获取进行中任务失败' };
    }
  }

  // 获取支持导入的站点列表
  const getSupportedImportSites = async () => {
    try {
      const response = await axios.get('/api/subscription/import/sites');
      if (response.data.code === 0) {
        return { success: true, data: response.data.data.sites || [] };
      }
      throw new Error(response.data.msg || '获取站点列表失败');
    } catch (error) {
      console.error('获取站点列表失败:', error);
      return { success: false, error: error.message || '获取站点列表失败' };
    }
  };

  // 预览订阅列表
  const previewImportSubscriptions = async (site) => {
    try {
      const response = await axios.get(`/api/subscription/import/${site}/preview`);
      if (response.data.code === 0) {
        return { success: true, data: response.data.data };
      }
      throw new Error(response.data.msg || '预览失败');
    } catch (error) {
      console.error('预览订阅失败:', error);
      const errorMessage = error.message || '预览失败';
      displayToast(errorMessage, { type: 'error' });
      return { success: false, error: errorMessage };
    }
  };

  // 执行导入
  const importSubscriptions = async (site) => {
    try {
      const response = await axios.post(`/api/subscription/import/${site}`);
      if (response.data.code === 0) {
        displayToast('导入完成！', { type: 'success' });
        return { success: true, data: response.data.data };
      }
      throw new Error(response.data.msg || '导入失败');
    } catch (error) {
      console.error('导入订阅失败:', error);
      const errorMessage = error.message || '导入失败';
      displayToast(errorMessage, { type: 'error' });
      return { success: false, error: errorMessage };
    }
  };

  return {
    getSubscriptions,
    getSubscriptionDetail,
    unsubscribe,
    updateNsfwStatus,
    triggerRefresh,
    getRefreshStatus,
    getActiveRefreshTasks,
    getSupportedImportSites,
    previewImportSubscriptions,
    importSubscriptions
  };
}
