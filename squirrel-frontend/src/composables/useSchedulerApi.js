import { del, get, post, put } from '../utils/request'

export function useSchedulerApi() {
  // 获取调度器状态
  const getSchedulerStatus = async () => {
    return get('/api/scheduler/status')
  };

  // 获取任务统计信息
  const getTaskStatistics = async () => {
    return get('/api/scheduler/statistics')
  };

  // 获取定时任务列表
  const getScheduledTasks = async (params = {}) => {
    return get('/api/scheduler/tasks', params)
  };

  // 获取任务详情
  const getTaskDetail = async (taskId) => {
    return get(`/api/scheduler/tasks/${taskId}`)
  };

  // 创建新任务
  const createTask = async (taskData) => {
    return post('/api/scheduler/tasks', taskData)
  };

  // 更新任务
  const updateTask = async (taskId, taskData) => {
    return put(`/api/scheduler/tasks/${taskId}`, taskData)
  };

  // 删除任务
  const deleteTask = async (taskId) => {
    return del(`/api/scheduler/tasks/${taskId}`)
  };

  // 启用任务
  const enableTask = async (taskId) => {
    return post(`/api/scheduler/tasks/${taskId}/enable`, null)
  };

  // 禁用任务
  const disableTask = async (taskId) => {
    return post(`/api/scheduler/tasks/${taskId}/disable`, null)
  };

  // 立即执行任务
  const executeTaskNow = async (taskId) => {
    return post(`/api/scheduler/tasks/${taskId}/execute`, null)
  };

  // 获取可用任务类
  const getAvailableTaskClasses = async () => {
    return get('/api/scheduler/task-classes')
  };

  // 获取任务执行日志
  const getTaskExecutionLogs = async (taskId = null, params = {}) => {
    const url = taskId ? `/api/scheduler/tasks/${taskId}/logs` : '/api/scheduler/logs'
    return get(url, params)
  };

  // 启用调度器
  const enableScheduler = async () => {
    return post('/api/scheduler/enable', null)
  };

  // 禁用调度器
  const disableScheduler = async () => {
    return post('/api/scheduler/disable', null)
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
