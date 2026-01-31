import { del, get, post, put } from '@/utils/request'

export const getSchedulerStatus = async () => {
  return get('/api/scheduler/status')
}

export const getTaskStatistics = async () => {
  return get('/api/scheduler/statistics')
}

export const getScheduledTasks = async (params = {}) => {
  return get('/api/scheduler/tasks', params)
}

export const getTaskDetail = async (taskId) => {
  return get(`/api/scheduler/tasks/${taskId}`)
}

export const createTask = async (taskData) => {
  return post('/api/scheduler/tasks', taskData)
}

export const updateTask = async (taskId, taskData) => {
  return put(`/api/scheduler/tasks/${taskId}`, taskData)
}

export const deleteTask = async (taskId) => {
  return del(`/api/scheduler/tasks/${taskId}`)
}

export const enableTask = async (taskId) => {
  return post(`/api/scheduler/tasks/${taskId}/enable`, null)
}

export const disableTask = async (taskId) => {
  return post(`/api/scheduler/tasks/${taskId}/disable`, null)
}

export const executeTaskNow = async (taskId) => {
  return post(`/api/scheduler/tasks/${taskId}/execute`, null)
}

export const getAvailableTaskClasses = async () => {
  return get('/api/scheduler/task-classes')
}

export const enableScheduler = async () => {
  return post('/api/scheduler/enable', null)
}

export const disableScheduler = async () => {
  return post('/api/scheduler/disable', null)
}
