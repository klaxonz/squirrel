import axios from '../utils/axios';

export function useSchedulerApi() {

  // 获取调度器状态
  const getSchedulerStatus = async () => {
    try {
      const response = await axios.get('/api/scheduler/status');
      return {
        success: true,
        data: response.data
      };
    } catch (error) {
      console.error('获取调度器状态失败:', error);
      return {
        success: false,
        error: error.message || '获取调度器状态失败'
      };
    }
  };

  // 获取任务统计信息
  const getTaskStatistics = async () => {
    try {
      const response = await axios.get('/api/scheduler/statistics');
      return {
        success: true,
        data: response.data
      };
    } catch (error) {
      console.error('获取任务统计失败:', error);
      return {
        success: false,
        error: error.message || '获取任务统计失败'
      };
    }
  };

  // 获取定时任务列表
  const getScheduledTasks = async (params = {}) => {
    try {
      const response = await axios.get('/api/scheduler/tasks', { params });
      return {
        success: true,
        data: response.data
      };
    } catch (error) {
      console.error('获取定时任务列表失败:', error);
      return {
        success: false,
        error: error.message || '获取定时任务列表失败'
      };
    }
  };

  // 获取任务详情
  const getTaskDetail = async (taskId) => {
    try {
      const response = await axios.get(`/api/scheduler/tasks/${taskId}`);
      return {
        success: true,
        data: response.data
      };
    } catch (error) {
      console.error('获取任务详情失败:', error);
      return {
        success: false,
        error: error.message || '获取任务详情失败'
      };
    }
  };

  // 创建新任务
  const createTask = async (taskData) => {
    try {
      const response = await axios.post('/api/scheduler/tasks', taskData);
      return {
        success: true,
        data: response.data.data
      };
    } catch (error) {
      console.error('创建任务失败:', error);
      const errorMessage = error.response?.data?.detail || error.message || '创建任务失败';
      return {
        success: false,
        error: errorMessage
      };
    }
  };

  // 更新任务
  const updateTask = async (taskId, taskData) => {
    try {
      const response = await axios.put(`/api/scheduler/tasks/${taskId}`, taskData);
      return {
        success: true,
        data: response.data
      };
    } catch (error) {
      console.error('更新任务失败:', error);
      const errorMessage = error.response?.data?.detail || error.message || '更新任务失败';
      return {
        success: false,
        error: errorMessage
      };
    }
  };

  // 删除任务
  const deleteTask = async (taskId) => {
    try {
      const response = await axios.delete(`/api/scheduler/tasks/${taskId}`);
      return {
        success: true,
        data: response.data
      };
    } catch (error) {
      console.error('删除任务失败:', error);
      const errorMessage = error.response?.data?.detail || error.message || '删除任务失败';
      return {
        success: false,
        error: errorMessage
      };
    }
  };

  // 启用任务
  const enableTask = async (taskId) => {
    try {
      const response = await axios.post(`/api/scheduler/tasks/${taskId}/enable`);
      return {
        success: true,
        data: response.data
      };
    } catch (error) {
      console.error('启用任务失败:', error);
      const errorMessage = error.response?.data?.detail || error.message || '启用任务失败';
      return {
        success: false,
        error: errorMessage
      };
    }
  };

  // 禁用任务
  const disableTask = async (taskId) => {
    try {
      const response = await axios.post(`/api/scheduler/tasks/${taskId}/disable`);
      return {
        success: true,
        data: response.data
      };
    } catch (error) {
      console.error('禁用任务失败:', error);
      const errorMessage = error.response?.data?.detail || error.message || '禁用任务失败';
      return {
        success: false,
        error: errorMessage
      };
    }
  };

  // 立即执行任务
  const executeTaskNow = async (taskId) => {
    try {
      const response = await axios.post(`/api/scheduler/tasks/${taskId}/execute`);
      return {
        success: true,
        data: response.data
      };
    } catch (error) {
      console.error('执行任务失败:', error);
      const errorMessage = error.response?.data?.detail || error.message || '执行任务失败';
      return {
        success: false,
        error: errorMessage
      };
    }
  };

  // 获取可用任务类
  const getAvailableTaskClasses = async () => {
    try {
      const response = await axios.get('/api/scheduler/task-classes');
      return {
        success: true,
        data: response.data
      };
    } catch (error) {
      console.error('获取可用任务类失败:', error);
      return {
        success: false,
        error: error.message || '获取可用任务类失败'
      };
    }
  };

  // 获取任务执行日志
  const getTaskExecutionLogs = async (taskId = null, params = {}) => {
    try {
      const url = taskId ? `/api/scheduler/tasks/${taskId}/logs` : '/api/scheduler/logs';
      const response = await axios.get(url, { params });
      return {
        success: true,
        data: response.data
      };
    } catch (error) {
      console.error('获取任务执行日志失败:', error);
      return {
        success: false,
        error: error.message || '获取任务执行日志失败'
      };
    }
  };

  // 启用调度器
  const enableScheduler = async () => {
    try {
      const response = await axios.post('/api/scheduler/enable');
      return {
        success: true,
        data: response.data
      };
    } catch (error) {
      console.error('启用调度器失败:', error);
      const errorMessage = error.message || '启用调度器失败';
      return {
        success: false,
        error: errorMessage
      };
    }
  };

  // 禁用调度器
  const disableScheduler = async () => {
    try {
      const response = await axios.post('/api/scheduler/disable');
      return {
        success: true,
        data: response.data
      };
    } catch (error) {
      console.error('禁用调度器失败:', error);
      const errorMessage = error.message || '禁用调度器失败';
      return {
        success: false,
        error: errorMessage
      };
    }
  };

  return {
    getSchedulerStatus,
    getTaskStatistics,
    getScheduledTasks,
    getTaskDetail,
    createTask,
    updateTask,
    deleteTask,
    enableTask,
    disableTask,
    executeTaskNow,
    getAvailableTaskClasses,
    getTaskExecutionLogs,
    enableScheduler,
    disableScheduler
  };
}
