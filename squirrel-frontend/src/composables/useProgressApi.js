import axios from '../utils/axios';

/**
 * 进度跟踪 API
 */
export function useProgressApi() {
  
  /**
   * 查询进度列表
   */
  const getProgressList = async (params = {}) => {
    try {
      const response = await axios.get('/api/progress/list', { params });
      if (response.data.code === 0) {
        return {
          success: true,
          data: response.data.data
        };
      } else {
        throw new Error(response.data.msg || '获取进度列表失败');
      }
    } catch (error) {
      console.error('获取进度列表失败:', error);
      return {
        success: false,
        error: error.message || '获取进度列表失败'
      };
    }
  };

  /**
   * 获取trace_id的最新进度
   */
  const getLatestProgressByTraceId = async (traceId) => {
    try {
      const response = await axios.get(`/api/progress/trace/${traceId}/latest`);
      if (response.data.code === 0) {
        return {
          success: true,
          data: response.data.data
        };
      } else {
        if (response.data.code === -1 && response.data.msg.includes('未找到')) {
          return {
            success: true,
            data: null
          };
        }
        throw new Error(response.data.msg || '获取进度失败');
      }
    } catch (error) {
      if (error.response?.status === 404) {
        return {
          success: true,
          data: null
        };
      }
      console.error('获取最新进度失败:', error);
      return {
        success: false,
        error: error.message || '获取进度失败'
      };
    }
  };

  /**
   * 获取进度时间线
   */
  const getProgressTimeline = async (params = {}) => {
    try {
      const response = await axios.get('/api/progress/timeline', { params });
      if (response.data.code === 0) {
        return {
          success: true,
          data: response.data.data
        };
      } else {
        throw new Error(response.data.msg || '获取时间线失败');
      }
    } catch (error) {
      console.error('获取进度时间线失败:', error);
      return {
        success: false,
        error: error.message || '获取时间线失败'
      };
    }
  };

  /**
   * 获取进度统计
   */
  const getProgressStatistics = async () => {
    try {
      const response = await axios.get('/api/progress/statistics');
      if (response.data.code === 0) {
        return {
          success: true,
          data: response.data.data
        };
      } else {
        throw new Error(response.data.msg || '获取统计失败');
      }
    } catch (error) {
      console.error('获取进度统计失败:', error);
      return {
        success: false,
        error: error.message || '获取统计失败'
      };
    }
  };

  return {
    getProgressList,
    getLatestProgressByTraceId,
    getProgressTimeline,
    getProgressStatistics
  };
}

